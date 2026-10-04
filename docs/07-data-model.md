# 7. Модель данных (IDEF1X / ER)

## Mermaid (erDiagram)

```mermaid
erDiagram
    SREDSTVO_NABLYUDENIYA ||--o{ ZHURNAL_OBSLUZHIVANIYA : "обслуживается"
    SREDSTVO_NABLYUDENIYA ||--o{ SEANS_NABLYUDENIYA : "используется в"
    KOSMICHESKIY_OBEKT ||--o{ SEANS_NABLYUDENIYA : "наблюдается в"
    KOSMICHESKIY_OBEKT ||--o{ PROGNOZ_DVIZHENIYA : "имеет прогноз"
    OPASNOE_SBLIZHENIE ||--|{ UCHASTNIK_SBLIZHENIYA : "включает"
    KOSMICHESKIY_OBEKT ||--o{ UCHASTNIK_SBLIZHENIYA : "участвует в"
    OPASNOE_SBLIZHENIE ||--o{ UVEDOMLENIE : "порождает"
    VLADELETS_SPUTNIKA ||--o{ UVEDOMLENIE : "получает"
    UVEDOMLENIE ||--o| REAKTSIYA_VLADELTSA : "имеет реакцию"

    SREDSTVO_NABLYUDENIYA {
        int id_sredstva PK
        string tip_sredstva
        string zona_obzora
        float chuvstvitelnost
        string rezhim_raboty
        string status
    }
    ZHURNAL_OBSLUZHIVANIYA {
        int id_zapisi PK
        datetime data_nachala_prostoya
        datetime data_okonchaniya_prostoya
        string prichina
        int kolichestvo_poteryannykh_seansov
        int id_sredstva FK
    }
    SEANS_NABLYUDENIYA {
        int id_seansa PK
        datetime data_vremya
        string poluchennye_dannye
        string rezultat_obrabotki
        int id_sredstva FK
        int katalozhnyy_nomer FK
    }
    KOSMICHESKIY_OBEKT {
        int katalozhnyy_nomer PK
        string mezhdunarodnyy_identifikator
        string tip_obekta
        float razmernaya_otsenka
        string orbitalnye_elementy
        string status
        datetime data_poslednego_nablyudeniya
    }
    PROGNOZ_DVIZHENIYA {
        int id_prognoza PK
        string orbitalnye_elementy
        string vremennoy_gorizont
        datetime data_rascheta
        int katalozhnyy_nomer FK
    }
    OPASNOE_SBLIZHENIE {
        int id_sblizheniya PK
        datetime vremya_sblizheniya
        float minimalnoe_rasstoyanie
        float veroyatnost_stolknoveniya
        string status
    }
    UCHASTNIK_SBLIZHENIYA {
        int id_sblizheniya PK, FK
        int katalozhnyy_nomer PK, FK
    }
    VLADELETS_SPUTNIKA {
        int id_vladeltsa PK
        string naimenovanie_organizatsii
        string kontaktnye_dannye
    }
    UVEDOMLENIE {
        int id_uvedomleniya PK
        string rekomendatsiya_po_manevru
        datetime data_otpravki
        int id_sblizheniya FK
        int id_vladeltsa FK
    }
    REAKTSIYA_VLADELTSA {
        int id_reaktsii PK
        string tip_reaktsii
        datetime data_fiksatsii
        int id_uvedomleniya FK
    }
```

> В Mermaid `erDiagram` имена сущностей и атрибутов записаны транслитом: кириллица в идентификаторах этого типа диаграмм поддерживается нестабильно. Соответствие: `SREDSTVO_NABLYUDENIYA` — Средство_наблюдения, `KOSMICHESKIY_OBEKT` — Космический_объект и т. д.

## PlantUML

Исходник с кириллическими именами: [07-data-model.puml](07-data-model.puml). Рисунок из отчёта:

![Рис. 7](img/fig7-idef1x.png)

[← к диаграммам](README.md)
