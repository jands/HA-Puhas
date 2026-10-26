# Puhas – Home Assistant

<img src="custom_components/puhas/brand/logo.png" alt="Puhas Oy" width="240">

Epävirallinen Home Assistant -integraatio, joka hakee jäteastioiden seuraavat tyhjennyspäivät
[Puhas Oy:n asiointipalvelusta](https://www.asiointipuhas.fi/) (Pohjois-Karjala).

*Unofficial Home Assistant integration that shows the next waste container collection dates
for customers of Puhas Oy (asiointipuhas.fi).*

## Ominaisuudet

- Asennus ja asetukset käyttöliittymästä (ei YAML:ää)
- `Seuraava tyhjennys` -sensori: lähin tuleva tyhjennys kaikista astioista (attribuutti `containers` kertoo, mitkä astiat)
- `Seuraava tyhjennys (teksti)` -sensori: sama tekstinä viikonpäivän kanssa, esim. `ma 2.11.2026` – sopii suoraan kojelaudalle ja ilmoituksiin
- Päivämääräsensorien attribuutit `formatted` (`ma 2.11.2026`) ja `weekday` (`maanantai`); kielenä suomi, jos Home Assistantin kieli on suomi, muuten englanti
- Oma päivämääräsensori jokaiselle astialle (esim. poltettava jäte, biojäte)
- Päivitys 6 tunnin välein, uudelleenkirjautumisen tuki salasanan vaihtuessa
- Suomenkieliset ja englanninkieliset tekstit

## Asennus

### HACS
1. HACS → ⋮ → *Custom repositories* → lisää tämän repositorion osoite, tyyppi *Integration*
2. Asenna **Puhas** ja käynnistä Home Assistant uudelleen

### Käsin
Kopioi kansio `custom_components/puhas` Home Assistantin `config/custom_components/`-kansioon ja käynnistä uudelleen.

## Käyttöönotto

*Asetukset → Laitteet ja palvelut → Lisää integraatio → Puhas*

- **Asiakasnumero**: muotoa `82-0001234-00`
- **Salasana**: asiointipuhas.fi-palvelun salasana (ensimmäisellä kirjautumiskerralla laskun numero – kirjaudu kerran selaimella ja vaihda salasana)

## Esimerkkiautomaatio: muistutus edellisenä iltana

```yaml
automation:
  - alias: "Roskis ulos huomenna"
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: template
        value_template: >
          {{ states('sensor.SINUN_KOHTEESI_seuraava_tyhjennys') | as_datetime | as_local
             | as_timestamp | int
             == (now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
             | as_timestamp | int }}
    actions:
      - action: notify.notify
        data:
          message: "Roskiksen tyhjennys huomenna – vie astia tien varteen."
```

(Tarkista sensorin entiteettitunnus kohdasta *Asetukset → Entiteetit*.)

## Huomioita

- Integraatio käyttää samoja rajapintoja kuin asiointipalvelun verkkosivu. Jos Puhas muuttaa sivustoaan, integraatio voi lakata toimasta – tee silloin issue.
- Tunnukset tallennetaan Home Assistantin asetuksiin (kuten muillakin integraatioilla).
- Projekti ei ole Puhas Oy:n tuote eikä sen hyväksymä. Puhas Oy:n logo on yhtiön tavaramerkki ja sitä käytetään tässä vain tunnistamaan palvelu; jos julkaiset repositorion avoimesti, kysy luvat Puhas Oy:ltä tai poista `brand`-kansio.
