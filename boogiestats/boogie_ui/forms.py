from django import forms

from boogiestats.boogie_api.models import Player


class EditPlayerForm(forms.ModelForm):
    gs_api_key = forms.CharField(
        min_length=32,
        max_length=32,
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "First 32 characters of your new GS API key"}),
        help_text="Fill this when you've generated a new GS API key",
        label="New GrooveStats API key",
    )

    class Meta:
        model = Player
        fields = ["machine_tag", "name", "pull_gs_name_and_tag", "leaderboard_source", "rivals", "gs_api_key"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclude "ourselves" from the possible rival list in the form
        self.fields["rivals"].queryset = Player.objects.exclude(api_key=self.instance.api_key)

    def save(self, commit=True):
        self.full_clean()
        if gs_api_key := self.cleaned_data["gs_api_key"]:
            bs_api_key = Player.gs_api_key_to_bs_api_key(gs_api_key)
            self.instance.api_key = bs_api_key

        return super().save(commit)
