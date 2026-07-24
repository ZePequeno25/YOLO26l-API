"""
Utility module to translate YOLO class names to friendly Portuguese descriptions.
"""

TRANSLATIONS = {
    # EPI e Segurança
    "fall-detected": "Queda Detectada",
    "gloves": "Luvas",
    "goggles": "Óculos de Proteção",
    "hardhat": "Capacete de Segurança",
    "ladder": "Escada",
    "mask": "Máscara",
    "no-gloves": "Sem Luvas",
    "no-goggles": "Sem Óculos de Proteção",
    "no-hardhat": "Sem Capacete de Segurança",
    "no-mask": "Sem Máscara",
    "no-safety vest": "Sem Colete de Segurança",
    "no_safety_vest": "Sem Colete de Segurança",
    "safety cone": "Cone de Segurança",
    "safety vest": "Colete de Segurança",
    "safety_vest": "Colete de Segurança",
    "person": "Pessoa",
    "chair": "Cadeira",
    
    # Veículos e Máquinas Pesadas
    "car": "Carro",
    "truck": "Caminhão",
    "excavators": "Escavadeira",
    "excavator": "Escavadeira",
    "dump truck": "Caminhão Caçamba",
    "dump_truck": "Caminhão Caçamba",
    "wheel loader": "Carregadeira",
    "concrete_mixer_truck": "Caminhão Betoneira",
    "dump": "Caçamba",
    "big bus": "Ônibus Grande",
    "big truck": "Caminhão Grande",
    "bus-l-": "Ônibus Longo",
    "bus-s-": "Ônibus Pequeno",
    "mid truck": "Caminhão Médio",
    "small bus": "Micro-ônibus",
    "small truck": "Caminhão Pequeno",
    "truck-l-": "Caminhão Grande",
    "truck-m-": "Caminhão Médio",
    "truck-s-": "Caminhão Pequeno",
    "truck-xl-": "Caminhão Extra Grande",
    "bull_dozer": "Trator de Esteira (Bulldozer)",
    "dumb_truck": "Caminhão Caçamba",
    "grader": "Motoniveladora",
    "loader": "Carregadeira",
    "mobile_crane": "Guindaste Móvel",
    "roller": "Rolo Compressor",
    
    # Extintores
    "babcock davis co2 portable": "Extintor CO2 Babcock Davis",
    "walker fire mc-2a co2": "Extintor CO2 Walker MC-2A",
    "walker fire mf-60 foam": "Extintor Espuma Walker MF-60",
    "yamato ya-10nx": "Extintor Yamato YA-10NX",
    "fire extinguisher": "Extintor de Incêndio",
    
    # Caixas e Embalagens
    "box": "Caixa",
    "boxes": "Caixas",
    "container": "Contêiner",
    "forklift": "Empilhadeira",
    "closed-box": "Caixa Fechada",
    "open-box": "Caixa Aberta",
    "packets": "Pacotes",
    "background box": "Caixa de Fundo",
    "labels": "Etiquetas",
    "product": "Produto",
    
    # Objetos Diversos
    "license_plate": "Placa de Veículo",
    "parking-sign": "Placa de Estacionamento",
    "space-empty": "Vaga Vazia",
    "space-occupied": "Vaga Ocupada",
    "brown_glass_bottle": "Garrafa de Vidro Escura",
    "clear_glass_bottle": "Garrafa de Vidro Transparente",
    "glass bottle": "Garrafa de Vidro",
    
    # Alimentos / Supermercado
    "apple": "Maçã",
    "bag": "Sacola",
    "bag_noodles": "Miojo de Pacote",
    "banana": "Banana",
    "bottledrink": "Garrafa de Bebida",
    "bowl_noodles": "Miojo de Copo",
    "boxcookies": "Caixa de Biscoitos",
    "can": "Lata",
    "canchips": "Batata em Lata",
    "candrinks": "Lata de Refrigerante",
    "chips": "Batatinha",
    "cookie": "Biscoito",
    "dragoneye": "Pitaia (Olho de Dragão)",
    "eggroll": "Rolinho Primavera",
    "fagao": "Fagão",
    "firedragon": "Fruta do Dragão",
    "grapes": "Uvas",
    "kiwi": "Kiwi",
    "liuding": "Laranja Liuding",
    "malao": "Malao",
    "mango": "Manga",
    "melon": "Melão",
    "onehand": "Uma Mão",
    "orange": "Laranja",
    "pear": "Pera",
    "pineapple": "Abacaxi",
    "rice": "Arroz",
    "science": "Ciência",
    "shize": "Shize",
    "shoutao": "Shoutao",
    "snow": "Neve",
    "sweetcan": "Lata de Doce",
    "turtle": "Tartaruga",
    "watermelon": "Melancia",
    "wong": "Wong",
    "yuzi": "Yuzi",
    "zaozi": "Zaozi"
}

def translate_class_name(name: str) -> str:
    """
    Traduz o nome de uma classe para português.
    Retorna o nome original sanitizado caso não haja tradução direta mapeada.
    """
    if not name:
        return ""
    
    # Chave de busca direta
    key = name.strip().lower()
    if key in TRANSLATIONS:
        return TRANSLATIONS[key]
        
    # Busca com hífens e underscores substituídos por espaços
    key_normalized = key.replace("_", " ").replace("-", " ")
    if key_normalized in TRANSLATIONS:
        return TRANSLATIONS[key_normalized]
        
    # Verificação por substrings comuns
    translations_partial = {
        "fire extinguisher": "Extintor de Incêndio",
        "hardhat": "Capacete de Segurança",
        "safety vest": "Colete de Segurança",
        "goggles": "Óculos de Proteção",
        "gloves": "Luvas",
        "mask": "Máscara",
        "cone": "Cone de Segurança",
        "truck": "Caminhão",
        "bus": "Ônibus",
        "car": "Carro",
        "chair": "Cadeira",
        "person": "Pessoa"
    }
    
    for english, portuguese in translations_partial.items():
        if english in key_normalized:
            return portuguese
            
    # Fallback: tradução básica do prefixo 'no'
    friendly = key_normalized
    if friendly.startswith("no "):
        friendly = "sem " + friendly[3:]
    elif friendly.startswith("no_"):
        friendly = "sem " + friendly[3:]
        
    return friendly.title()
