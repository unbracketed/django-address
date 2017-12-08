from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.fields.related import ForeignObject
try:
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
except ImportError:
    from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor as ForwardManyToOneDescriptor
from django.utils.encoding import python_2_unicode_compatible

import logging
logger = logging.getLogger(__name__)

# Python 3 fixes.
import sys
if sys.version > '3':
    long = int
    basestring = (str, bytes)
    unicode = str

__all__ = ['Country', 'State', 'Locality', 'Address', 'AddressField']

class InconsistentDictError(Exception):
    pass

def _to_python(value):
    raw = value.get('raw', '')
    country = value.get('country', '')
    country_code = value.get('country_code', '')
    state = value.get('state', '')
    state_code = value.get('state_code', '')
    locality = value.get('locality', '')
    sublocality = value.get('sublocality', '')
    postal_code = value.get('postal_code', '')
    street_number = value.get('street_number', '')
    route = value.get('route', '')
    formatted = value.get('formatted', '')
    latitude = value.get('latitude', None)
    longitude = value.get('longitude', None)

    # If there is no value (empty raw) then return None.
    if not raw:
        return None

    # Fix issue with NYC boroughs (https://code.google.com/p/gmaps-api-issues/issues/detail?id=635)
    if not locality and sublocality:
        locality = sublocality

    # If we have an inconsistent set of value bail out now.
    if (country or state or locality) and not (country and state and locality):
        raise InconsistentDictError

    # Handle the country.
    try:
        country_obj = Country.objects.get(name=country)
    except Country.DoesNotExist:
        if country:
            if len(country_code) > Country._meta.get_field('code').max_length:
                if country_code != country:
                    raise ValueError('Invalid country code (too long): %s'%country_code)
                country_code = ''
            country_obj = Country.objects.create(name=country, code=country_code)
        else:
            country_obj = None

    # Handle the state.
    try:
        state_obj = State.objects.get(name=state, country=country_obj)
    except State.DoesNotExist:
        if state:
            if len(state_code) > State._meta.get_field('code').max_length:
                if state_code != state:
                    raise ValueError('Invalid state code (too long): %s'%state_code)
                state_code = ''
            state_obj = State.objects.create(name=state, code=state_code, country=country_obj)
        else:
            state_obj = None

    # Handle the locality.
    try:
        locality_obj = Locality.objects.get(name=locality, postal_code=postal_code, state=state_obj)
    except Locality.DoesNotExist:
        if locality:
            locality_obj = Locality.objects.create(name=locality, postal_code=postal_code, state=state_obj)
        else:
            locality_obj = None

    # Handle the address.
    try:
        if not (street_number or route or locality):
            address_obj = Address.objects.get(raw=raw)
        else:
            address_obj = Address.objects.get(
                street_number=street_number,
                route=route,
                locality=locality_obj
            )
    except Address.DoesNotExist:
        address_obj = Address(
            street_number=street_number,
            route=route,
            raw=raw,
            locality=locality_obj,
            formatted=formatted,
            latitude=latitude,
            longitude=longitude,
        )

        # If "formatted" is empty try to construct it from other values.
        if not address_obj.formatted:
            address_obj.formatted = unicode(address_obj)

        # Need to save.
        address_obj.save()

    # Done.
    return address_obj

##
## Convert a dictionary to an address.
##
def to_python(value):

    # Keep `None`s.
    if value is None:
        return None

    # Is it already an address object?
    if isinstance(value, Address):
        return value

    # If we have an integer, assume it is a model primary key. This is mostly for
    # Django being a cunt.
    elif isinstance(value, (int, long)):
        return value

    # A string is considered a raw value.
    elif isinstance(value, basestring):
        obj = Address(raw=value)
        obj.save()
        return obj

    # A dictionary of named address components.
    elif isinstance(value, dict):

        # Attempt a conversion.
        try:
            return _to_python(value)
        except InconsistentDictError:
            return Address.objects.create(raw=value['raw'])

    # Not in any of the formats I recognise.
    raise ValidationError('Invalid address value.')

##
## A country.
##
@python_2_unicode_compatible
class Country(models.Model):
    name = models.CharField(max_length=40, unique=True)
    code = models.CharField(max_length=2, blank=True) # not unique as there are duplicates (IT)

    class Meta:
        verbose_name_plural = 'Countries'
        ordering = ('name',)

    def __str__(self):
        return '%s'%(self.name or self.code)

##
## A state. Google refers to this as `administration_level_1`.
##
@python_2_unicode_compatible
class State(models.Model):
    """Google maps address component - administrative_area_level_1"""
    name = models.CharField(max_length=165)
    code = models.CharField(max_length=3, blank=True)
    country = models.ForeignKey(Country, related_name='states',
                                on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'country')
        ordering = ('country', 'name')

    def __str__(self):
        txt = self.to_str()
        country = '%s'%self.country
        if country and txt:
            txt += ', '
        txt += country
        return txt

    def to_str(self):
        return '%s'%(self.name or self.code)

###
### County
###
@python_2_unicode_compatible
class Admin2(models.Model):
    """
    Google maps address component - administrative_area_level_2
    In the US, this corresponds to a county. 
    """
    name = models.CharField(max_length=165, blank=True, default="")
    state = models.ForeignKey(State, related_name='counties',
                              on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'state')
        ordering = ('state', 'name')

    def __str__(self):
        txt = "{} - {} - {}".format(self.name,
                                    self.state.name,
                                    self.state.country.name)
        return txt

###
### Admin 3 - unincorporated area
###
@python_2_unicode_compatible
class Admin3(models.Model):
    """
    Google maps address component - administrative_area_level_3
    In the US, this is an unincorporated area or township. 
    Used in place of locality  when unavailable.
    """
    name = models.CharField(max_length=165)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    parent = models.ForeignKey(Admin2, blank=True, null=True,
                               on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'state')
        ordering = ('state', 'parent', 'name')

    def __str__(self):
        txt = "{}, {} - {}".format(name, state.code, country.name)
        return txt


@python_2_unicode_compatible
class Admin4(models.Model):
    """
    Google maps address component - administrative_area_level_4
    """
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(Admin3, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)


@python_2_unicode_compatible
class Admin5(models.Model):
    """
    Google maps address component - administrative_area_level_5
    """
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(Admin4, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)


##
## A locality (suburb).
##
@python_2_unicode_compatible
class Locality(models.Model):
    """ Google maps address component - locality"""
    name = models.CharField(max_length=165)
    postal_code = models.CharField(max_length=10, blank=True)
    state = models.ForeignKey(State, related_name='localities',
                              on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Localities'
        unique_together = ('name', 'postal_code', 'state')
        ordering = ('state', 'name')

    def __str__(self):
        txt = '%s'%self.name
        state = self.state.to_str() if self.state else ''
        if txt and state:
            txt += ', '
        txt += state
        if self.postal_code:
            txt += ' %s'%self.postal_code
        cntry = '%s'%(self.state.country if self.state and self.state.country else '')
        if cntry:
            txt += ', %s'%cntry
        return txt

###
### sublocality (level 1 if multiple)
###
class SubLocality1(models.Model):
    """ Google maps address component - sublocality or sublocality_level_1"""
    name = models.CharField(max_length=165)
    locality = models.ForeignKey(Locality, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'locality')
        ordering = ('name', 'locality')

    def __str__(self):
        return "{}, {}".format(self.name, self.locality)

###
### sublocality level 2
###    
class SubLocality2(models.Model):
    """ Google maps address component - sublocality_level_2"""
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(SubLocality1, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)


###
### sublocality level 3
###    
class SubLocality3(models.Model):
    """ Google maps address component - sublocality_level_3"""
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(SubLocality2, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)

    
###
### sublocality level 4
###    
class SubLocality4(models.Model):
    """ Google maps address component - sublocality_level_4"""
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(SubLocality3, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')    

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)


###
### sublocality level 5
###    
class SubLocality5(models.Model):
    """ Google maps address component - sublocality_level_5"""
    name = models.CharField(max_length=165)
    parent = models.ForeignKey(SubLocality4, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'parent')
        ordering = ('parent', 'name')    

    def __str__(self):
        return "{}, {}".format(self.name, self.parent)


class Neighborhood(models.Model):

    name = models.CharField(max_length=165)
    locality = models.ForeignKey(Locality, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'locality')
        ordering = ('locality', 'name')

    def __str__(self):
        return "{}, {}".format(self.name, self.locality)


class Airport(models.Model):
    name = models.CharField(max_length=165, unique=True)

    def __str__(self):
        return self.name


class PostalCode(models.Model):
    code = models.CharField(max_length=15)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('code', 'country')
        ordering = ('country', 'code')

    def __str__(self):
        return "{} - {}".format(self.code, self.country)


class PostalCodeSuffix(models.Model):
    suffix = models.CharField(max_length=15)
    code = models.ForeignKey(PostalCode, on_delete=models.CASCADE)

    class Meta:
        unique_together =  ('suffix', 'code')
        ordering = ('code', 'suffix')

    def __str__(self):
        return "{}-{}".format(self.code, self.suffix)

    
##
## An address. If for any reason we are unable to find a matching
## decomposed address we will store the raw address string in `raw`.
##
@python_2_unicode_compatible
class Address(models.Model):
    street_number = models.CharField(max_length=20, blank=True)
    route = models.CharField(max_length=100, blank=True)
    locality = models.ForeignKey(Locality, related_name='addresses',
                                 blank=True, null=True,
                                 on_delete=models.CASCADE)
    raw = models.CharField(max_length=200)
    formatted = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    intersection = models.CharField(max_length=165, blank=True,
                                    default="")
    colloquial_area = models.CharField(max_length=165, blank=True,
                                       default="")
    neighborhood = models.ForeignKey(Neighborhood, blank=True,
                                     null=True, on_delete=models.CASCADE)
    airport = models.ForeignKey(Airport, blank=True, null=True,
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ('locality', 'route', 'street_number')
        # unique_together = ('locality', 'route', 'street_number')

    def __str__(self):
        if self.formatted != '':
            txt = '%s'%self.formatted
        elif self.locality:
            txt = ''
            if self.street_number:
                txt = '%s'%self.street_number
            if self.route:
                if txt:
                    txt += ' %s'%self.route
            locality = '%s'%self.locality
            if txt and locality:
                txt += ', '
            txt += locality
        else:
            txt = '%s'%self.raw
        return txt

    def clean(self):
        if not self.raw:
            raise ValidationError('Addresses may not have a blank `raw` field.')

    def as_dict(self):
        ad = dict(
            street_number=self.street_number,
            route=self.route,
            raw=self.raw,
            formatted=self.formatted,
            latitude=self.latitude if self.latitude else '',
            longitude=self.longitude if self.longitude else '',
        )
        if self.locality:
            ad['locality'] = self.locality.name
            ad['postal_code'] = self.locality.postal_code
            if self.locality.state:
                ad['state'] = self.locality.state.name
                ad['state_code'] = self.locality.state.code
                if self.locality.state.country:
                    ad['country'] = self.locality.state.country.name
                    ad['country_code'] = self.locality.state.country.code
        return ad

class AddressDescriptor(ForwardManyToOneDescriptor):

    def __set__(self, inst, value):
        super(AddressDescriptor, self).__set__(inst, to_python(value))

##
## A field for addresses in other models.
##
class AddressField(models.ForeignKey):
    description = 'An address'

    def __init__(self, *args, **kwargs):
        kwargs['to'] = 'address.Address'
        super(AddressField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, virtual_only=False):
        super(ForeignObject, self).contribute_to_class(cls, name)
        setattr(cls, self.name, AddressDescriptor(self))

    # def deconstruct(self):
    #     name, path, args, kwargs = super(AddressField, self).deconstruct()
    #     del kwargs['to']
    #     return name, path, args, kwargs

    def formfield(self, **kwargs):
        from .forms import AddressField as AddressFormField
        defaults = dict(form_class=AddressFormField)
        defaults.update(kwargs)
        return super(AddressField, self).formfield(**defaults)
