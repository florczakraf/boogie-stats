from django import forms
from django.db import transaction
from formset.forms import FormMixin
from formset.renderers.bootstrap import FormRenderer
from formset.widgets import DualSelector

from boogiestats.boogie_api.choices import IdentityProvider
from boogiestats.boogie_api.models import Player


class EditPlayerForm(FormMixin, forms.ModelForm):
    gs_api_key = forms.CharField(
        min_length=32,
        max_length=32,
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "First 32 characters of your new GS API key"}),
        help_text="Warning: Fill this *only* when you've generated a new GS API key",
        label="New GrooveStats API key",
    )
    rivals = forms.models.ModelMultipleChoiceField(
        queryset=Player.objects.all(),
        widget=DualSelector(search_lookup=["name__icontains", "machine_tag__icontains"]),
        required=False,
    )

    field_css_classes = "row mb-3"
    field_with_spacer_css_classes = f"{field_css_classes} horizontal-spacer"
    default_renderer = FormRenderer(
        label_css_classes="col-sm-3 fw-bold",
        control_css_classes="col-sm-9",
        field_css_classes={
            "*": field_css_classes,
            "twitch_handle": field_with_spacer_css_classes,
            "gs_api_key": field_with_spacer_css_classes,
        },
    )

    class Meta:
        model = Player
        fields = [
            "machine_tag",
            "name",
            "gs_integration",
            "leaderboard_source",
            "pull_gs_name_and_tag",
            "rivals",
            "twitch_handle",
            "discord_handle",
            "youtube_handle",
            "twitter_x_handle",
            "bokutachi_handle",
            "kamaitachi_handle",
            "bluesky_handle",
            "gs_api_key",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclude "ourselves" from the possible rival list in the form
        self.fields["rivals"].queryset = Player.objects.exclude(pk=self.instance.pk)

    def save(self, commit=True):
        self.full_clean()
        if gs_api_key := self.cleaned_data["gs_api_key"]:
            self._rotate_gs_api_key_identity(gs_api_key)

        return super().save(commit)

    @transaction.atomic
    def _rotate_gs_api_key_identity(self, gs_api_key):
        # changing the key replaces the old one, i.e. the old key stops working
        self.instance.identities.filter(provider=IdentityProvider.GS_API_KEY).delete()
        self.instance.identities.create(
            provider=IdentityProvider.GS_API_KEY,
            external_id=Player.gs_api_key_to_bs_api_key(gs_api_key),
        )
