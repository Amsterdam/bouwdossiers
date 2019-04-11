import glob
import logging
import re

import xmltodict
from django.db import transaction

from . import models

from stadsarchief.settings import DATA_DIR

log = logging.getLogger(__name__)

MAP_STADSDEEL_NAAM_CODE = {
    'Zuidoost': 'T',
    'Centrum': 'A',
    'Noord': 'N',
    'Westpoort': 'B',
    'West': 'E',
    'Nieuw-West': 'F',
    'Zuid': 'K',
    'Oost': 'M',
}


def get_datering(value):
    result = None
    if value:
        if len(value) == 4:
            result = f"{value}-01-01"
        else:
            m = re.search("([0-9]{1,2})-([0-9]{4})", value)
            if m:
                result = f"{m.group(2)}-{m.group(1)}-01"
            else:
                log.warning(f"Unexpected datering pattern {value}")
                result = None
    return result


def get_list_items(d, key1, key2):
    x = d.get(key1)
    if x:
        items = x.get(key2)
        if items and not isinstance(items, list):
            items = [items]
        if items:
            return items
    return []


def delete_all():
    models.Pand.objects.all().delete()
    models.Nummeraanduiding.objects.all().delete()
    models.Bestand.objects.all().delete()
    models.SubDossier.objects.all().delete()
    models.Adres.objects.all().delete()
    models.BouwDossier.objects.all().delete()


def import_bouwdossiers():
    with transaction.atomic():
        delete_all()

    total_count = 0
    root_dir = DATA_DIR
    for file_path in glob.iglob(root_dir + '/**/*.xml', recursive=True):
        log.info(f"Processing - {file_path}")
        count = 0

        # SAA_BWT_Stadsdeel_Centrum_02.xml
        m = re.search('SAA_BWT_Stadsdeel_([^_]+)_\\d{1,5}\\.xml$', file_path)
        if m:
            stadsdeel_naam = m.group(1)
            with open(file_path) as fd:
                xml = xmltodict.parse(fd.read())

            with transaction.atomic():
                for x_dossier in get_list_items(xml, 'bwtDossiers', 'dossier'):
                    dossiernr = x_dossier['dossierNr']
                    stadsdeel = MAP_STADSDEEL_NAAM_CODE[stadsdeel_naam]
                    titel = x_dossier['titel']
                    if not titel:
                        titel = ''
                        log.warning(f"Missing titel for bouwdossier {dossiernr} in {file_path}")

                    datering = get_datering(x_dossier.get('datering'))
                    dossier_type = x_dossier.get('dossierType')

                    bouwdossier = models.BouwDossier(
                        dossiernr=dossiernr,
                        stadsdeel=stadsdeel,
                        titel=titel,
                        datering=datering,
                        dossier_type=dossier_type,
                    )
                    bouwdossier.save()
                    count += 1
                    total_count += 1

                    if total_count % 1000 == 0:
                        log.info(f"Bouwdossiers count in file: {count}, total: {total_count}")

                    for x_adres in get_list_items(x_dossier, 'adressen', 'adres'):
                        huisnummer_van = x_adres.get('huisnummerVan')
                        huisnummer_van = int(huisnummer_van) if huisnummer_van else None
                        huisnummer_tot = x_adres.get('huisnummerTot')
                        huisnummer_tot = int(huisnummer_tot) if huisnummer_tot else None

                        adres = models.Adres(
                            bouwdossier=bouwdossier,
                            straat=x_adres['straat'],
                            huisnummer_van=huisnummer_van,
                            huisnummer_tot=huisnummer_tot,
                            stadsdeel=stadsdeel
                        )
                        adres.save()

                    for x_sub_dossier in get_list_items(x_dossier, 'subDossiers', 'subDossier'):
                        titel = x_sub_dossier['titel']

                        if not titel:
                            titel = ''
                            log.warning(f"Missing titel for subdossier for {bouwdossier.dossiernr} in {file_path}")

                        sub_dossier = models.SubDossier(
                            bouwdossier=bouwdossier,
                            titel=titel
                        )
                        sub_dossier.save()

                        bestanden = [
                            models.Bestand(
                                subdossier=sub_dossier,
                                dossier=bouwdossier,
                                name=x_bestand
                            ) for x_bestand in get_list_items(x_sub_dossier, 'bestanden', 'bestand')
                        ]
                        models.Bestand.objects.bulk_create(bestanden)
    log.info(f"Import finished. Bouwdossiers total: {total_count}")
