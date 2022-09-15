from django import forms

from boogiestats.boogie_api.models import Player


class EditPlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["machine_tag", "rivals", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclude "ourselves" from the possible rival list in the form
        self.fields["rivals"].queryset = Player.objects.exclude(api_key=self.instance.api_key)
