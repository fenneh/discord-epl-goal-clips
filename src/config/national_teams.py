"""National team configs for World Cup 2026 coverage.

Covers confirmed qualifiers and other reasonably-likely participants. Flags
served from flagcdn.com (height 120 renders cleanly as a Discord embed
thumbnail). Colours are flag-derived or kit-primary.

Schema matches premier_league_teams: name, aliases, color, logo.
"""


def _flag(iso2: str) -> str:
    return f"https://flagcdn.com/h120/{iso2}.png"


national_teams = {
    # CONCACAF - hosts
    "USA": {
        "name": "United States",
        "aliases": ["USA", "United States", "USMNT", "US", "U.S.", "U.S.A.", "America"],
        "color": 0x002868,
        "logo": _flag("us"),
    },
    "Mexico": {
        "name": "Mexico",
        "aliases": ["Mexico", "México", "El Tri", "Tri", "MEX"],
        "color": 0x006847,
        "logo": _flag("mx"),
    },
    "Canada": {
        "name": "Canada",
        "aliases": ["Canada", "Les Rouges"],
        "color": 0xD52B1E,
        "logo": _flag("ca"),
    },
    # CONCACAF - other
    "Costa Rica": {
        "name": "Costa Rica",
        "aliases": ["Costa Rica", "Los Ticos"],
        "color": 0xCE1126,
        "logo": _flag("cr"),
    },
    "Panama": {
        "name": "Panama",
        "aliases": ["Panama", "Panamá", "La Marea Roja"],
        "color": 0xC8102E,
        "logo": _flag("pa"),
    },
    "Jamaica": {
        "name": "Jamaica",
        "aliases": ["Jamaica", "Reggae Boyz"],
        "color": 0x009B3A,
        "logo": _flag("jm"),
    },
    "Honduras": {
        "name": "Honduras",
        "aliases": ["Honduras", "Los Catrachos"],
        "color": 0x0073CF,
        "logo": _flag("hn"),
    },
    # CONMEBOL
    "Argentina": {
        "name": "Argentina",
        "aliases": ["Argentina", "La Albiceleste"],
        "color": 0x75AADB,
        "logo": _flag("ar"),
    },
    "Brazil": {
        "name": "Brazil",
        "aliases": ["Brazil", "Brasil", "Seleção", "Selecao", "Canarinho"],
        "color": 0xFEDF00,
        "logo": _flag("br"),
    },
    "Uruguay": {
        "name": "Uruguay",
        "aliases": ["Uruguay", "La Celeste"],
        "color": 0x4189DD,
        "logo": _flag("uy"),
    },
    "Colombia": {
        "name": "Colombia",
        "aliases": ["Colombia", "Los Cafeteros"],
        "color": 0xFCD116,
        "logo": _flag("co"),
    },
    "Ecuador": {
        "name": "Ecuador",
        "aliases": ["Ecuador", "La Tri"],
        "color": 0xFFD100,
        "logo": _flag("ec"),
    },
    "Paraguay": {
        "name": "Paraguay",
        "aliases": ["Paraguay", "La Albirroja"],
        "color": 0xD52B1E,
        "logo": _flag("py"),
    },
    "Chile": {
        "name": "Chile",
        "aliases": ["Chile", "La Roja"],
        "color": 0xD52B1E,
        "logo": _flag("cl"),
    },
    "Bolivia": {
        "name": "Bolivia",
        "aliases": ["Bolivia", "La Verde"],
        "color": 0x007934,
        "logo": _flag("bo"),
    },
    "Venezuela": {
        "name": "Venezuela",
        "aliases": ["Venezuela", "La Vinotinto"],
        "color": 0x7E2A3B,
        "logo": _flag("ve"),
    },
    "Peru": {
        "name": "Peru",
        "aliases": ["Peru", "Perú", "La Blanquirroja"],
        "color": 0xD91023,
        "logo": _flag("pe"),
    },
    # UEFA
    "England": {
        "name": "England",
        "aliases": ["England", "Three Lions", "ENG"],
        "color": 0xFFFFFF,
        "logo": _flag("gb-eng"),
    },
    "France": {
        "name": "France",
        "aliases": ["France", "Les Bleus"],
        "color": 0x002654,
        "logo": _flag("fr"),
    },
    "Germany": {
        "name": "Germany",
        "aliases": ["Germany", "Die Mannschaft", "GER", "Deutschland"],
        "color": 0x000000,
        "logo": _flag("de"),
    },
    "Spain": {
        "name": "Spain",
        "aliases": ["Spain", "España", "Espana", "La Roja", "La Furia Roja", "ESP"],
        "color": 0xAA151B,
        "logo": _flag("es"),
    },
    "Portugal": {
        "name": "Portugal",
        "aliases": ["Portugal", "Seleção das Quinas", "POR"],
        "color": 0x046A38,
        "logo": _flag("pt"),
    },
    "Italy": {
        "name": "Italy",
        "aliases": ["Italy", "Italia", "Azzurri", "Gli Azzurri", "ITA"],
        "color": 0x0066CC,
        "logo": _flag("it"),
    },
    "Netherlands": {
        "name": "Netherlands",
        "aliases": ["Netherlands", "Holland", "Dutch", "Oranje", "NED", "The Netherlands"],
        "color": 0xFF6700,
        "logo": _flag("nl"),
    },
    "Belgium": {
        "name": "Belgium",
        "aliases": ["Belgium", "Red Devils", "Belgian Red Devils", "BEL"],
        "color": 0xC8102E,
        "logo": _flag("be"),
    },
    "Croatia": {
        "name": "Croatia",
        "aliases": ["Croatia", "Hrvatska", "Vatreni", "CRO"],
        "color": 0xFF0000,
        "logo": _flag("hr"),
    },
    "Switzerland": {
        "name": "Switzerland",
        "aliases": ["Switzerland", "Schweiz", "Suisse", "Nati", "SUI", "SWI"],
        "color": 0xDA291C,
        "logo": _flag("ch"),
    },
    "Denmark": {
        "name": "Denmark",
        "aliases": ["Denmark", "Danmark", "Danish Dynamite", "DEN"],
        "color": 0xC60C30,
        "logo": _flag("dk"),
    },
    "Austria": {
        "name": "Austria",
        "aliases": ["Austria", "Österreich", "Das Team", "AUT"],
        "color": 0xED2939,
        "logo": _flag("at"),
    },
    "Poland": {
        "name": "Poland",
        "aliases": ["Poland", "Polska", "Biało-czerwoni", "POL"],
        "color": 0xDC143C,
        "logo": _flag("pl"),
    },
    "Czechia": {
        "name": "Czechia",
        "aliases": ["Czechia", "Czech Republic", "Česko", "CZE"],
        "color": 0x11457E,
        "logo": _flag("cz"),
    },
    "Norway": {
        "name": "Norway",
        "aliases": ["Norway", "Norge", "NOR"],
        "color": 0xC8102E,
        "logo": _flag("no"),
    },
    "Sweden": {
        "name": "Sweden",
        "aliases": ["Sweden", "Sverige", "Blågult", "Blagult", "SWE"],
        "color": 0xFECC00,
        "logo": _flag("se"),
    },
    "Scotland": {
        "name": "Scotland",
        "aliases": ["Scotland", "Tartan Army", "SCO"],
        "color": 0x0065BD,
        "logo": _flag("gb-sct"),
    },
    "Wales": {
        "name": "Wales",
        "aliases": ["Wales", "Cymru", "Y Ddraig Goch", "WAL"],
        "color": 0xD30731,
        "logo": _flag("gb-wls"),
    },
    "Republic of Ireland": {
        "name": "Republic of Ireland",
        "aliases": ["Ireland", "Republic of Ireland", "Boys in Green", "IRL", "Eire", "Éire"],
        "color": 0x009A44,
        "logo": _flag("ie"),
    },
    "Northern Ireland": {
        "name": "Northern Ireland",
        "aliases": ["Northern Ireland", "Green and White Army", "NIR"],
        "color": 0x00A651,
        "logo": _flag("gb-nir"),
    },
    "Hungary": {
        "name": "Hungary",
        "aliases": ["Hungary", "Magyarország", "HUN"],
        "color": 0x008751,
        "logo": _flag("hu"),
    },
    "Serbia": {
        "name": "Serbia",
        "aliases": ["Serbia", "Srbija", "Orlovi", "SRB"],
        "color": 0xC6363C,
        "logo": _flag("rs"),
    },
    "Romania": {
        "name": "Romania",
        "aliases": ["Romania", "România", "Tricolorii", "ROU"],
        "color": 0xFCD116,
        "logo": _flag("ro"),
    },
    "Slovakia": {
        "name": "Slovakia",
        "aliases": ["Slovakia", "Slovensko", "SVK"],
        "color": 0x0B4EA2,
        "logo": _flag("sk"),
    },
    "Slovenia": {
        "name": "Slovenia",
        "aliases": ["Slovenia", "Slovenija", "SVN"],
        "color": 0x005DA4,
        "logo": _flag("si"),
    },
    "Greece": {
        "name": "Greece",
        "aliases": ["Greece", "Ελλάδα", "Galanolefki", "GRE"],
        "color": 0x0D5EAF,
        "logo": _flag("gr"),
    },
    "Turkey": {
        "name": "Turkey",
        "aliases": ["Turkey", "Türkiye", "Turkiye", "Ay-Yıldızlılar", "TUR"],
        "color": 0xE30A17,
        "logo": _flag("tr"),
    },
    "Ukraine": {
        "name": "Ukraine",
        "aliases": ["Ukraine", "Україна", "Zbirna", "UKR"],
        "color": 0x0057B7,
        "logo": _flag("ua"),
    },
    "Albania": {
        "name": "Albania",
        "aliases": ["Albania", "Shqipëria", "Kuq e Zinjtë", "ALB"],
        "color": 0xE41E20,
        "logo": _flag("al"),
    },
    # AFC
    "Japan": {
        "name": "Japan",
        "aliases": ["Japan", "Samurai Blue", "Nippon", "JPN"],
        "color": 0x0033A0,
        "logo": _flag("jp"),
    },
    "South Korea": {
        "name": "South Korea",
        "aliases": ["South Korea", "Korea Republic", "S. Korea", "Korea", "Taegeuk Warriors", "KOR"],
        "color": 0xCD2E3A,
        "logo": _flag("kr"),
    },
    "Iran": {
        "name": "Iran",
        "aliases": ["Iran", "IR Iran", "Team Melli", "Persia", "Persian", "IRN"],
        "color": 0x239F40,
        "logo": _flag("ir"),
    },
    "Saudi Arabia": {
        "name": "Saudi Arabia",
        "aliases": ["Saudi Arabia", "Saudis", "Green Falcons", "KSA"],
        "color": 0x006C35,
        "logo": _flag("sa"),
    },
    "Australia": {
        "name": "Australia",
        "aliases": ["Australia", "Socceroos", "AUS"],
        "color": 0xFFCD00,
        "logo": _flag("au"),
    },
    "Qatar": {
        "name": "Qatar",
        "aliases": ["Qatar", "The Maroons", "Al-Annabi", "QAT"],
        "color": 0x8A1538,
        "logo": _flag("qa"),
    },
    "Iraq": {
        "name": "Iraq",
        "aliases": ["Iraq", "Lions of Mesopotamia", "IRQ"],
        "color": 0xCE1126,
        "logo": _flag("iq"),
    },
    "United Arab Emirates": {
        "name": "United Arab Emirates",
        "aliases": ["United Arab Emirates", "UAE", "Al-Abyad"],
        "color": 0x00732F,
        "logo": _flag("ae"),
    },
    "Uzbekistan": {
        "name": "Uzbekistan",
        "aliases": ["Uzbekistan", "White Wolves", "UZB"],
        "color": 0x1EB53A,
        "logo": _flag("uz"),
    },
    "Jordan": {
        "name": "Jordan",
        "aliases": ["Jordan", "Al-Nashama", "JOR"],
        "color": 0x007A3D,
        "logo": _flag("jo"),
    },
    # CAF
    "Morocco": {
        "name": "Morocco",
        "aliases": ["Morocco", "Atlas Lions", "MAR"],
        "color": 0xC1272D,
        "logo": _flag("ma"),
    },
    "Senegal": {
        "name": "Senegal",
        "aliases": ["Senegal", "Lions of Teranga", "SEN"],
        "color": 0x00853F,
        "logo": _flag("sn"),
    },
    "Egypt": {
        "name": "Egypt",
        "aliases": ["Egypt", "Pharaohs", "The Pharaohs", "EGY"],
        "color": 0xCE1126,
        "logo": _flag("eg"),
    },
    "Algeria": {
        "name": "Algeria",
        "aliases": ["Algeria", "Les Fennecs", "Desert Foxes", "ALG", "DZA"],
        "color": 0x006233,
        "logo": _flag("dz"),
    },
    "Tunisia": {
        "name": "Tunisia",
        "aliases": ["Tunisia", "Eagles of Carthage", "TUN"],
        "color": 0xE70013,
        "logo": _flag("tn"),
    },
    "Nigeria": {
        "name": "Nigeria",
        "aliases": ["Nigeria", "Super Eagles", "NGA"],
        "color": 0x008753,
        "logo": _flag("ng"),
    },
    "Ivory Coast": {
        "name": "Ivory Coast",
        "aliases": ["Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire", "Cote dIvoire", "Les Éléphants", "CIV"],
        "color": 0xFF8200,
        "logo": _flag("ci"),
    },
    "Ghana": {
        "name": "Ghana",
        "aliases": ["Ghana", "Black Stars", "GHA"],
        "color": 0xFCD116,
        "logo": _flag("gh"),
    },
    "Cameroon": {
        "name": "Cameroon",
        "aliases": ["Cameroon", "Indomitable Lions", "CMR"],
        "color": 0x007A5E,
        "logo": _flag("cm"),
    },
    "South Africa": {
        "name": "South Africa",
        "aliases": ["South Africa", "Bafana Bafana", "RSA"],
        "color": 0x007749,
        "logo": _flag("za"),
    },
    "Mali": {
        "name": "Mali",
        "aliases": ["Mali", "Les Aigles", "MLI"],
        "color": 0x14B53A,
        "logo": _flag("ml"),
    },
    "Burkina Faso": {
        "name": "Burkina Faso",
        "aliases": ["Burkina Faso", "Étalons", "Stallions", "BFA"],
        "color": 0xEF2B2D,
        "logo": _flag("bf"),
    },
    "Cape Verde": {
        "name": "Cape Verde",
        "aliases": ["Cape Verde", "Cabo Verde", "Tubarões Azuis", "CPV"],
        "color": 0x003893,
        "logo": _flag("cv"),
    },
    "DR Congo": {
        "name": "DR Congo",
        "aliases": ["DR Congo", "Democratic Republic of the Congo", "Congo DR", "Léopards", "Leopards", "COD"],
        "color": 0x007FFF,
        "logo": _flag("cd"),
    },
    # OFC
    "New Zealand": {
        "name": "New Zealand",
        "aliases": ["New Zealand", "All Whites", "NZL"],
        "color": 0xFFFFFF,
        "logo": _flag("nz"),
    },
    # Late additions — qualified late or surprise qualifiers per ESPN's
    # WC 2026 fixture list.
    "Bosnia-Herzegovina": {
        "name": "Bosnia-Herzegovina",
        "aliases": [
            "Bosnia-Herzegovina",
            "Bosnia and Herzegovina",
            "Bosnia",
            "Zmajevi",
            "Dragons",
            "BIH",
        ],
        "color": 0x002F6C,
        "logo": _flag("ba"),
    },
    "Curaçao": {
        "name": "Curaçao",
        "aliases": ["Curaçao", "Curacao", "CUW"],
        "color": 0x002B7F,
        "logo": _flag("cw"),
    },
    "Haiti": {
        "name": "Haiti",
        "aliases": ["Haiti", "Haïti", "Les Grenadiers", "HAI", "HTI"],
        "color": 0xD21034,
        "logo": _flag("ht"),
    },
}
