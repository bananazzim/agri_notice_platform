from __future__ import annotations

from django import forms

from .models import Agency, EmailSubscription


class EmailSubscriptionForm(forms.ModelForm):
    keywords = forms.CharField(
        label="관심 키워드",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "예: 스마트팜, 청년농, 창업",
            }
        ),
        help_text="쉼표로 여러 키워드를 입력할 수 있습니다.",
    )
    email = forms.EmailField(
        label="이메일",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
            }
        ),
    )
    agencies = forms.ModelMultipleChoiceField(
        label="관심 기관",
        queryset=Agency.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="선택하지 않으면 모든 기관을 대상으로 알림을 보냅니다.",
    )

    class Meta:
        model = EmailSubscription
        fields = ["email", "keywords", "agencies"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agencies"].queryset = Agency.objects.filter(is_active=True).order_by(
            "crawler_priority",
            "name",
        )

    def clean_keywords(self) -> str:
        keywords = self.cleaned_data["keywords"]
        normalized = [
            keyword.strip()
            for keyword in keywords.replace("\n", ",").split(",")
            if keyword.strip()
        ]
        if not normalized:
            raise forms.ValidationError("하나 이상의 키워드를 입력하세요.")
        if len(normalized) > 20:
            raise forms.ValidationError("키워드는 최대 20개까지 등록할 수 있습니다.")
        return ", ".join(dict.fromkeys(normalized))
