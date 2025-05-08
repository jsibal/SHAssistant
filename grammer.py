# actions
ACTION = {
    "on": {"zapnout", "zapni", "zapní", "rozsviť", "zapny", "zapný", "rozsvit"},
    "off": {"vypni", "zhasni", "zhasnout", "vybni", "vybní", "vypní"},
    "set": {"nastav", "dej", "přepni na"},
    "end": {"konec", "skonči", "ukončit"},
    "back": {"zpět", "vrátit", "vrátit se", "nazpět"},
    "cancel": {"zruš", "nech být", "zahodit",  "stop","zahoď", "zrušit" , "ukonči akci"},
    "start": {"start", "zapni poslech", "ok domove", "začínáme"}
}

# potvrzení
BOOL_RESPONSE = {
    True: {"ano", "jo", "chci", "určitě", "správně", "presně", "potvrzuji", "potvrzuju", "ok", "potvrdit"},
    False: {"ne", "nechci", "vůbec", "zamítnout"}
}

# zařízení
DEVICE = {
    "light": {"světlo"},
    "climate": {"topení", "teplotu"}
}

# teploty
TEMPERATURE = {
    "15": {"15", "patnáct"},
    "16": {"16", "šestnáct"},
    "17": {"17", "sedmnáct"},
    "18": {"18", "osmnáct"},
    "19": {"19", "devatenáct"},
    "20": {"20", "dvacet"},
    "21": {"21", "dvacet jedna", "jedna a dvacet", "jedenadvacet"},
    "22": {"22", "dvacet dva", "dva a dvacet", "dvaadvacet"},
    "23": {"23", "dvacet tři", "tři a dvacet", "třiadvacet"},
    "24": {"24", "dvacet čtyři", "čtyři a dvacet", "čtyřiadvacet"},
    "25": {"25", "dvacet pět", "pět a dvacet", "pětadvacet"},
    "26": {"26", "dvacet šest", "šest a dvacet", "šestadvacet"},
    "27": {"27", "dvacet sedm", "sedm a dvacet", "sedmadvacet"},
    "28": {"28", "dvacet osm", "osm a dvacet", "osmadevadesát"},
    "29": {"29", "dvacet devět", "devět a dvacet", "devětadvacet"},
    "30": {"30", "třicet"}
}
BRIGHTNESS = {
    "25": {"velmi nízký", "25"},
    "50": {"nízký", "nízká", "málo", "tlumené", "50","ztlum", "méně", "trochu",'padesát'},
    "100": {"střední", "normální", "100"},
    "170": {"vysoký", "hodně", "silný", "jasné", "170","jasněji"},
    "255": {"velmi vysoký", "plný", "maximum", "max","naplno", "maximálně", "255", "co nejvíc"}
}

COLOR = {
    "red": {"červená", "červené", "červený", "červeně", "červena", "červene"},
    "green": {"zelená", "zelené", "zelený", "zelene", "zeleně", "zelena"},
    "blue": {"modrá", "modré", "modrý", "modrou", "modravá", "modra","modre","modře"},
    "white": {"bílá", "bílé", "bílý", "bíla",  "byla"},
    "yellow": {"žlutá", "žluté", "žlutý", "žlutě", "žlute", "žluta"},
    "purple": {"fialová", "fialova","fialové", "fialový", "fialova","fialově","fialove"},
    "orange": {"oranžová","oranžově","oranžove", "oranžové", "oranžový", "oranžova", "oranžova"},
    "pink": {"růžová", "růžové", "růžový", "světle růžová", "sytě růžová", "růžova"},
    "cyan": {"tyrkysová", "azurová", "cyanová", "do tyrkysova", "světle modrozelená"},
    "warmwhite": {"teplá bílá", "teplé světlo", "žlutobílá", "útulné světlo", "teplá barva", "žluto bílé", "žluto bílá"},
    "coldwhite": {"studená bílá", "chladná bílá", "modrobílá", "chladná barva", "modrobílé", "studené světlo"}
}


QUERY_TYPE = {
    "temperature": {"jaká je teplota","jaka je teplota", "jak teplo je","jaké teplo je", "jake teplo je", "kolik je stupňů"},
    "state": {"je zapnuto", "je vypnuto", "svítí", "je zapnuté", "je zapnuto","funguje"},
    "brightness": {"jak silné", "jaký je jas", "intenzita", "jak moc svítí"},
    "color": {"jaká je barva", "jak svítí", "barevné světlo", "jakou má barvu"}
}

