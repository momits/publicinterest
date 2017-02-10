from django.contrib.gis import admin
from django import forms

# Register models for the admin interface.

from .models import Player, Role, Engagement, Medium, Statement, Publication, Topic, Translatable, Translation


class EngagementInline(admin.TabularInline):
    model = Engagement
    extra = 1


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    inlines = [
        EngagementInline,
    ]

admin.site.register(Role)


class StatementAdminForm(forms.ModelForm):
    orig_content = forms.CharField()

    class Meta:
        model = Statement
        exclude = ('content',)


@admin.register(Statement)
class StatementAdmin(admin.OSMGeoAdmin):
    exclude = ('content',)
    form = StatementAdminForm

    def save_model(self, request, statement, form, change):
        if not change:
            # The statement was just created. We have to create a new translatable corresponding
            # to the statement content and the original language.
            statement.content = Translatable.with_translation(form.cleaned_data['language'],
                                                              form.cleaned_data['orig_content'])
        elif 'content' in form.changed_data:
            # The wording in the original language was corrected.
            statement.content.set_translation(form.cleaned_data['language'],
                                              form.cleaned_data['orig_content'])

        super(StatementAdmin, self).save_model(request, statement, form, change)

admin.site.register(Topic)

admin.site.register(Medium)
admin.site.register(Publication)