from __future__ import annotations

import discord
from discord.components import MediaGalleryItem
from discord.ui import Container, MediaGallery, Separator, TextDisplay

from ballsdex.core.discord import LayoutView
from fcdex_3_1.fcdex_ext.pack_assets import pack_art_path
from fcdex_3_1.fcdex_ext.views import truncate_text
from fcdex_3_1.models import PackType


def pack_art_file(pack_type: str) -> discord.File | None:
    path = pack_art_path(pack_type)
    if not path.is_file():
        return None
    return discord.File(str(path), filename=path.name)


def build_pack_open_layout(*, pack_type: str, body: str) -> tuple[LayoutView, list[discord.File]]:
    pack_label = PackType(pack_type).label
    art = pack_art_file(pack_type)
    attachments: list[discord.File] = []

    layout = LayoutView()
    container = Container()
    if art is not None:
        attachments.append(art)
        container.add_item(MediaGallery(MediaGalleryItem(media=f"attachment://{art.filename}", description=pack_label)))
        container.add_item(Separator())
    container.add_item(TextDisplay(truncate_text(f"# 📦 {pack_label}\n\n{body}")))
    layout.add_item(container)
    return layout, attachments
