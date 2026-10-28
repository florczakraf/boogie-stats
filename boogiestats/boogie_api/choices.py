from django.db import models


class LeaderboardSource(models.IntegerChoices):
    BS = 1, "BoogieStats"
    GS = 2, "GrooveStats"


class GSIntegration(models.IntegerChoices):
    REQUIRE = 1, "Require GrooveStats"
    TRY = 2, "Try GrooveStats"
    SKIP = 3, "Skip GrooveStats"


class IdentityProvider(models.TextChoices):
    GS_API_KEY = "gs_api_key", "GrooveStats API key"


class GSStatus(models.IntegerChoices):
    OK = 1, "OK"
    ERROR = 2, "An error occurred during submission (GS might have accepted the score)"
    SKIPPED = 3, "Submission was skipped"
