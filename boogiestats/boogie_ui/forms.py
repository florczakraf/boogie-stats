from django import forms
from formset.forms import FormMixin
from formset.renderers.bootstrap import FormRenderer
from formset.widgets import DualSelector

from boogiestats.boogie_api.models import Player


class EditPlayerForm(FormMixin, forms.ModelForm):
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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclude "ourselves" from the possible rival list in the form
        self.fields["rivals"].queryset = Player.objects.exclude(pk=self.instance.pk)


class AddIdentityForm(forms.Form):
    gs_api_key = forms.CharField(
        min_length=32,
        max_length=32,
        required=True,
        widget=forms.PasswordInput(attrs={"placeholder": "First 32 characters of your GS API key"}),
        help_text="First 32 characters of the GrooveStats API key you want to attach to your profile.",
        label="GrooveStats API key",
    )
