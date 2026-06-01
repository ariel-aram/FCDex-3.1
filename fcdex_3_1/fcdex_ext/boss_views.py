from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import ActionRow, Button, Container, Modal, Separator, TextDisplay, TextInput, View, button

from ballsdex.core.discord import LayoutView
from bd_models.models import Ball, BallInstance, Player
from fcdex_3_1.fcdex_ext import boss_raid
from fcdex_3_1.fcdex_ext.boss_raid import get_raid
from fcdex_3_1.fcdex_ext.views import AdminHubBackRow, truncate_text

if TYPE_CHECKING:
    from discord import Interaction

log = logging.getLogger("fcdex_3_1.boss.views")


class BossJoinView(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=900)
        self.guild_id = guild_id

    @discord.ui.button(label="Join boss raid", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def join(self, interaction: Interaction, button: discord.ui.Button):
        raid = get_raid(self.guild_id)
        if raid is None:
            await interaction.response.send_message("This raid has ended.", ephemeral=True)
            return
        ok, message = boss_raid.join_raid(raid, interaction.user.id)
        await interaction.response.send_message(message, ephemeral=True)


class StartBossModal(Modal, title="Start boss raid"):
    hp = TextInput(label="Boss HP", placeholder="10000", max_length=12, default="10000")

    def __init__(self, owner_id: int, boss_ball: Ball):
        super().__init__()
        self.owner_id = owner_id
        self.boss_ball = boss_ball

    async def on_submit(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("Boss raids must be started in a server.", ephemeral=True)
            return
        try:
            hp = int(self.hp.value.strip().replace(",", ""))
            if hp < 100:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("HP must be at least 100.", ephemeral=True)
            return
        try:
            raid = boss_raid.start_raid(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,  # type: ignore[union-attr]
                boss_ball=self.boss_ball,
                hp=hp,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        emoji = interaction.client.get_emoji(self.boss_ball.emoji_id) if self.boss_ball.emoji_id else "👹"
        view = BossJoinView(interaction.guild.id)
        try:
            file = None
            if self.boss_ball.collection_card:
                ext = self.boss_ball.collection_card.name.split(".")[-1]
                file = discord.File(str(self.boss_ball.collection_card.path), filename=f"boss.{ext}")
            content = (
                f"# Boss raid — {emoji} **{self.boss_ball.country}**\n"
                f"-# HP: **{raid.current_hp:,}** · Join below, then admins run rounds in `/fcdex admin` → Boss."
            )
            msg = await interaction.channel.send(content=content, file=file, view=view)  # type: ignore[union-attr]
            raid.announcement_message_id = msg.id
            view.message = msg
        except Exception:
            log.exception("Failed to post boss announcement")

        layout = await build_boss_admin_layout(
            self.owner_id,
            interaction.guild.id,
            notice="Raid started in this channel.",
        )
        await interaction.response.edit_message(view=layout)


class BossPlayerCardSelect(discord.ui.Select):
    def __init__(self, owner_id: int, instances: list[BallInstance]):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=f"#{inst.pk}",
                value=str(inst.pk),
                description=(inst.ball.country if hasattr(inst, "ball") else "?")[:100],
            )
            for inst in instances[:25]
        ]
        super().__init__(placeholder="Pick a clubball for this round…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction) -> None:
        if interaction.guild is None:
            return
        raid = get_raid(interaction.guild.id)
        if raid is None:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This menu is private to you.", ephemeral=True)
            return
        inst = await BallInstance.objects.select_related("ball", "player").aget(pk=int(self.values[0]))
        player, _ = await Player.objects.aget_or_create(discord_id=interaction.user.id)
        if inst.player_id != player.pk:
            await interaction.response.send_message("That card is not yours.", ephemeral=True)
            return
        ok, message = await boss_raid.submit_card(raid, interaction.user.id, inst)
        layout = await build_boss_player_layout(interaction.user.id, interaction.guild.id, notice=message)
        await interaction.response.edit_message(view=layout)


class BossStartBallSelect(discord.ui.Select):
    def __init__(self, owner_id: int, balls: list[Ball]):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=b.country[:100], value=str(b.pk), description=f"r:{b.rarity}"[:100])
            for b in balls[:25]
        ]
        super().__init__(placeholder="Choose clubball as boss…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This panel is not yours.", ephemeral=True)
            return
        ball = await Ball.objects.aget(pk=int(self.values[0]))
        await interaction.response.send_modal(StartBossModal(self.owner_id, ball))


class BossAdminControls(ActionRow):
    def __init__(self, owner_id: int, guild_id: int):
        super().__init__()
        self.owner_id = owner_id
        self.guild_id = guild_id

    @button(label="Attack round", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_round(self, interaction: Interaction, button: Button):
        await self._round(interaction, attack=True)

    @button(label="Defend round", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def defend_round(self, interaction: Interaction, button: Button):
        await self._round(interaction, attack=False)

    @button(label="Resolve", style=discord.ButtonStyle.primary, emoji="✅")
    async def resolve(self, interaction: Interaction, button: Button):
        raid = get_raid(self.guild_id)
        if raid is None:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return
        log_text = await boss_raid.resolve_round(raid)
        layout = await build_boss_admin_layout(self.owner_id, self.guild_id, notice=log_text)
        await interaction.response.edit_message(view=layout)

    @button(label="Conclude", style=discord.ButtonStyle.success, emoji="🏁")
    async def conclude(self, interaction: Interaction, button: Button):
        raid = get_raid(self.guild_id)
        if raid is None:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return
        summary, _ = await boss_raid.conclude_raid(raid, grant_reward=True)
        layout = await build_boss_admin_layout(self.owner_id, self.guild_id, notice=summary)
        await interaction.response.edit_message(view=layout)

    async def _round(self, interaction: Interaction, *, attack: bool) -> None:
        raid = get_raid(self.guild_id)
        if raid is None:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return
        ok, message = boss_raid.begin_round(raid, attack_phase=attack)
        layout = await build_boss_admin_layout(self.owner_id, self.guild_id, notice=message if ok else message)
        await interaction.response.edit_message(view=layout)


async def build_boss_player_layout(user_id: int, guild_id: int, *, notice: str = "") -> LayoutView:
    raid = get_raid(guild_id)
    layout = LayoutView(timeout=300)
    container = Container()

    if raid is None:
        container.add_item(TextDisplay("# 👑 Boss raid\n*No active raid in this server.*"))
        layout.add_item(container)
        return layout

    boss = await Ball.objects.aget(pk=raid.boss_ball_id)
    participant = raid.participants.get(user_id)
    header = (
        f"# 👑 {boss.country}\n"
        f"HP **{raid.current_hp:,}** / **{raid.max_hp:,}** · Round **{raid.round}** · phase `{raid.phase}`"
    )
    if notice:
        header += f"\n\n{notice}"
    if participant:
        header += f"\n\nYour damage: **{participant.total_damage:,}**"
    container.add_item(TextDisplay(truncate_text(header)))

    if raid.phase == "join":
        container.add_item(Separator())
        container.add_item(TextDisplay("-# Tap **Join** on the raid announcement, or ask an admin to start rounds."))
    elif raid.phase == "pick" and participant and not participant.disqualified:
        player = await Player.objects.filter(discord_id=user_id).afirst()
        if player:
            instances = [
                i
                async for i in BallInstance.objects.filter(player=player, deleted=False)
                .select_related("ball", "player")
                .order_by("-pk")[:25]
                if i.pk not in raid.used_instance_ids
            ]
            if instances:
                container.add_item(Separator())
                row = ActionRow()
                row.add_item(BossPlayerCardSelect(user_id, instances))
                container.add_item(row)

    layout.add_item(container)
    return layout


async def build_boss_admin_layout(owner_id: int, guild_id: int, *, notice: str = "") -> LayoutView:
    raid = get_raid(guild_id)
    layout = LayoutView(timeout=600)
    container = Container()

    if raid is None:
        body = (
            "*No raid — start one with **Start raid** "
            "(pick a clubball in the command options first via `/fcdex admin`).*"
        )
    else:
        boss = await Ball.objects.aget(pk=raid.boss_ball_id)
        body = (
            f"**{boss.country}** · HP **{raid.current_hp:,}** / **{raid.max_hp:,}**\n"
            f"Round **{raid.round}** · phase `{raid.phase}` · **{len(raid.alive_participant_ids)}** fighters\n\n"
            f"{boss_raid.standings(raid)}"
        )
    if notice:
        body = f"{notice}\n\n{body}"

    container.add_item(
        TextDisplay(
            truncate_text(
                "# 👑 Boss admin\n"
                "-# Inspired by BallsDex Boss Pack · Components v2.\n"
                "-# Requires a **Boss** special in your dex for winner rewards."
            )
        )
    )
    container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(body)))
    if raid is not None:
        container.add_item(Separator())
        container.add_item(BossAdminControls(owner_id, guild_id))
    else:
        balls = [b async for b in Ball.objects.filter(enabled=True).order_by("country")[:25]]
        if balls:
            container.add_item(Separator())
            row = ActionRow()
            row.add_item(BossStartBallSelect(owner_id, balls))
            container.add_item(row)
    container.add_item(Separator())
    container.add_item(AdminHubBackRow(owner_id, guild_id))
    layout.add_item(container)
    return layout
