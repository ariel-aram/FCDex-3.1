from typing import TYPE_CHECKING

from .achievement_cog import AchievementCog
from .battle_cog import BattleCog
from .merge_cog import MergeCog
from .tournament_cog import TournamentCog

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(BattleCog(bot))
    await bot.add_cog(MergeCog(bot))
    await bot.add_cog(AchievementCog(bot))
    await bot.add_cog(TournamentCog(bot))
