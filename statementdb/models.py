from django.utils.translation import ugettext as _
from django.contrib.gis.db import models


# Models of the statementdb.


# We currently support translations for the following languages:
LANGUAGES = (('de_de', _('German')), ('en_US', _('English')))

# The desired language is the following:
LOCALE = 'de_de'

# The size of the language codes in use.
LANG_CODE_LEN = 5

# The size where a string should be truncated.
TRUNCATE_AT_LENGTH = 60


def truncate(s, length):
    """
    Truncates a string s if it is too long and adds dots to indicate this.

    :param s: the string to truncate
    :param length: after this number of characters the string will be truncated
    :return: the truncated string
    """
    return (s[:length] + '..') if len(s) > length else s


class Translatable(models.Model):
    """
    Represents a translatable unit.
    """
    def __str__(self):
        translation = Translation.get(self)
        return truncate(translation, TRUNCATE_AT_LENGTH) if translation else 'Unused translatable.'

    @staticmethod
    def with_translation(language, translation):
        """
        Produces a new Translatable togethter with a translation in a certain language.
        :return: the new translatable
        """
        translatable = Translatable()
        translatable.save()

        # choose the way of storing the translation based on its length
        d = {'translatable': translatable,
             'language': language,
             'translation': translation}
        translation = ShortTranslation(d) if len(translation) <= ShortTranslation.MAX_LENGTH else LongTranslation(d)
        translation.save()

        return translatable

    def set_translation(self, language, translation):
        """
        Sets the translation of this translatable in the given language.

        :param language: the language the translation is for
        :param translation: the translation
        :return: None
        """
        if len(translation) <= ShortTranslation.MAX_LENGTH:
            # the translation must be stored as a short translation
            t = ShortTranslation.objects.filter(translatable=self, language=language)
            if t.exists():
                t.update(translation=translation)
            else:
                LongTranslation.objects.filter(translatable=self, language=language).delete()
                ShortTranslation({'translatable': self,
                                  'language': language,
                                  'translation': translation}).save()
        else:
            # the translation must be stored as a long translation
            t = LongTranslation.objects.filter(translatable=self, language=language)
            if t.exists():
                t.update(translation=translation)
            else:
                ShortTranslation.objects.filter(translatable=self, language=language).delete()
                LongTranslation({'translatable': self,
                                 'language': language,
                                 'translation': translation}).save()


class Translation(models.Model):
    """
    A translation translates a translatable into a specific language.
    This is an abstract superclass for ShortTranslation and LongTranslation.
    """

    # the translatable
    translatable = models.ForeignKey(Translatable)

    # the language of the translation
    language = models.CharField(max_length=LANG_CODE_LEN, choices=LANGUAGES)

    def __str__(self):
        return truncate(self.translation, TRUNCATE_AT_LENGTH)

    @staticmethod
    def get(f):
        r = Translation.objects.filter(translatable=f, language=LOCALE)
        return r.first().translation if r.exists() else None


class ShortTranslation(Translation):
    """
    A translation which has not more than 100 characters.
    """

    # the maximum length of short translations
    MAX_LENGTH = 100

    # the translation for the translatable
    translation = models.CharField(max_length=MAX_LENGTH)


class LongTranslation(Translation):
    """
    A translation which has more than 100 characters.
    """

    # the translation for the translatable
    translation = models.TextField()


class Player(models.Model):
    """
    A player is a person or an organization which regularly makes public statements.
    """

    # a player has a name
    name = models.CharField(max_length=200)

    # # a player has a date of birth or a founding date
    # start_date = models.DateField()
    #
    # # a player might have a date of death or a date of breakup
    # end_date = models.DateField(null=True, blank=True)

    # a player has certain (public) functions or professions over time
    role = models.ManyToManyField('Role', through='Engagement')

    def save(self, *args, **kwargs):
        # if self.end_date:
        #     assert self.start_date < self.end_date
        super(Player, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    A role is an official function or position a player had at a certain point in time.
    """

    # a role has a name
    name = models.ForeignKey(Translatable)

    def __str__(self):
        return Translation.get(self.name)


class Engagement(models.Model):
    """
    A player can be engaged in a role during a certain time period.
    """

    # an engagement has an engaging player
    player = models.ForeignKey(Player)

    # an engagement has a certain role
    role = models.ForeignKey(Role)

    # an engagement has started at a certain point in time
    start_date = models.DateField()

    # an engagement might have already ended at a certain point in time
    end_date = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.end_date:
            assert self.start_date < self.end_date
        super(Engagement, self).save(*args, **kwargs)


class Medium(models.Model):
    """
    A medium delivers information to the public.
    """

    # a medium has a name
    name = models.CharField(max_length=200)

    # a medium has an URL
    url = models.URLField()

    def __str__(self):
        return self.name


class Topic(models.Model):
    """
    A topic is an event or being in the world which is talked about in public.
    """

    # a topic has a short headline / abbreviation
    headline = models.ForeignKey(Translatable, related_name='topic_headlines')

    # a topic has a description
    description = models.ForeignKey(Translatable, related_name='topic_descriptions')

    def __str__(self):
        return Translation.get(self.headline)


class Statement(models.Model):
    """
    A statement is a sequence of sentences produced by a player at a certain point
    in time. A statement is *public*, iff it has been published by a medium.
    """

    # a statement is made by a player
    player = models.ForeignKey(Player, on_delete=models.CASCADE)

    # a statement is made in a certain language
    language = models.CharField(max_length=LANG_CODE_LEN, choices=LANGUAGES)

    # a statement has some content
    content = models.ForeignKey(Translatable)

    # a statement was produced at some point in time
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)

    # a statement was eventually produced at a certain location
    location = models.PointField(null=True, blank=True)

    # a statement might touch certain topics
    context = models.ManyToManyField(Topic, blank=True)

    # a statement can be documented by media
    publications = models.ManyToManyField(Medium, through='Publication')

    # a statement can reference other statements (answer, question, criticism, etc.)
    references = models.ManyToManyField('Statement', blank=True)

    def __str__(self):
        return '%(player)s stated "%(content)s" at %(location)s %(date)s' % {
            'player': str(self.player),
            'content': truncate(Translation.get(self.content), TRUNCATE_AT_LENGTH),
            'location': str(self.location),
            'date': str(self.date)
        }


class Publication(models.Model):
    """
    A publication is the appearance of a statement in a medium.
    """

    # a publication refers to one statement
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE)

    # a publication takes place in a medium
    medium = models.ForeignKey(Medium, on_delete=models.CASCADE)

    # a publication is made at some point in time
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)

    # a publication is referenced by an URL
    url = models.URLField()

    def __str__(self):
        return '"%(content)s" published in %(medium)s at %(date)s.' % {
            'content': truncate(self.statement.content, TRUNCATE_AT_LENGTH),
            'medium': str(self.medium),
            'date': str(self.date)
        }

