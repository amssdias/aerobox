from django import forms

from apps.cloud_storage.models import ShareLink


class ShareLinkAdminForm(forms.ModelForm):
    class Meta:
        model = ShareLink
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)

        if "password" in self.changed_data:
            raw_password = self.cleaned_data.get("password")
            if raw_password:
                instance.set_password(raw_password)

        if commit:
            instance.save()
        return instance
