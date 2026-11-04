"""Lugares que NO se anonimizan: comunas, ciudades, regiones y países.

Mantenerlos permite que la IA entienda el contexto geográfico (jurisdicción,
tribunal competente, etc.) sin exponer datos personales.
"""
import unicodedata

COMUNAS = """
Arica|Camarones|Putre|General Lagos|
Iquique|Alto Hospicio|Pozo Almonte|Camiña|Colchane|Huara|Pica|
Antofagasta|Mejillones|Sierra Gorda|Taltal|Calama|Ollagüe|San Pedro de Atacama|Tocopilla|María Elena|
Copiapó|Caldera|Tierra Amarilla|Chañaral|Diego de Almagro|Vallenar|Alto del Carmen|Freirina|Huasco|
La Serena|Coquimbo|Andacollo|La Higuera|Paiguano|Vicuña|Illapel|Canela|Los Vilos|Salamanca|Ovalle|
Combarbalá|Monte Patria|Punitaqui|Río Hurtado|
Valparaíso|Casablanca|Concón|Juan Fernández|Puchuncaví|Quintero|Viña del Mar|Isla de Pascua|Los Andes|
Calle Larga|Rinconada|San Esteban|La Ligua|Cabildo|Papudo|Petorca|Zapallar|Quillota|La Calera|Calera|
Hijuelas|La Cruz|Nogales|San Antonio|Algarrobo|Cartagena|El Quisco|El Tabo|Santo Domingo|San Felipe|
Catemu|Llaillay|Llay-Llay|Panquehue|Putaendo|Santa María|Quilpué|Limache|Olmué|Villa Alemana|
Santiago|Cerrillos|Cerro Navia|Conchalí|El Bosque|Estación Central|Huechuraba|Independencia|La Cisterna|
La Florida|La Granja|La Pintana|La Reina|Las Condes|Lo Barnechea|Lo Espejo|Lo Prado|Macul|Maipú|Ñuñoa|
Pedro Aguirre Cerda|Peñalolén|Providencia|Pudahuel|Quilicura|Quinta Normal|Recoleta|Renca|San Joaquín|
San Miguel|San Ramón|Vitacura|Puente Alto|Pirque|San José de Maipo|Colina|Lampa|Tiltil|Til Til|
San Bernardo|Buin|Calera de Tango|Paine|Melipilla|Alhué|Curacaví|María Pinto|San Pedro|Talagante|
El Monte|Isla de Maipo|Padre Hurtado|Peñaflor|
Rancagua|Codegua|Coinco|Coltauco|Doñihue|Graneros|Las Cabras|Machalí|Malloa|Mostazal|San Francisco de Mostazal|
Olivar|Peumo|Pichidegua|Quinta de Tilcoco|Rengo|Requínoa|San Vicente|San Vicente de Tagua Tagua|Pichilemu|
La Estrella|Litueche|Marchigüe|Navidad|Paredones|San Fernando|Chépica|Chimbarongo|Lolol|Nancagua|
Palmilla|Peralillo|Placilla|Pumanque|Santa Cruz|
Talca|Constitución|Curepto|Empedrado|Maule|Pelarco|Pencahue|Río Claro|San Clemente|San Rafael|
Cauquenes|Chanco|Pelluhue|Curicó|Hualañé|Licantén|Molina|Rauco|Romeral|Sagrada Familia|Teno|
Vichuquén|Linares|Colbún|Longaví|Parral|Retiro|San Javier|Villa Alegre|Yerbas Buenas|
Chillán|Bulnes|Chillán Viejo|El Carmen|Pemuco|Pinto|Quillón|San Ignacio|Yungay|Quirihue|Cobquecura|
Coelemu|Ninhue|Portezuelo|Ránquil|Treguaco|Trehuaco|San Carlos|Coihueco|Ñiquén|San Fabián|San Nicolás|
Concepción|Coronel|Chiguayante|Florida|Hualqui|Lota|Penco|San Pedro de la Paz|Santa Juana|Talcahuano|
Tomé|Hualpén|Lebu|Arauco|Cañete|Contulmo|Curanilahue|Los Álamos|Tirúa|Los Ángeles|Antuco|Cabrero|
Laja|Mulchén|Nacimiento|Negrete|Quilaco|Quilleco|San Rosendo|Santa Bárbara|Tucapel|Yumbel|Alto Biobío|
Temuco|Carahue|Cunco|Curarrehue|Freire|Galvarino|Gorbea|Lautaro|Loncoche|Melipeuco|Nueva Imperial|
Padre Las Casas|Perquenco|Pitrufquén|Pucón|Saavedra|Puerto Saavedra|Teodoro Schmidt|Toltén|Vilcún|
Villarrica|Cholchol|Angol|Collipulli|Curacautín|Ercilla|Lonquimay|Los Sauces|Lumaco|Purén|Renaico|
Traiguén|Victoria|
Valdivia|Corral|Lanco|Los Lagos|Máfil|Mariquina|San José de la Mariquina|Paillaco|Panguipulli|La Unión|
Futrono|Lago Ranco|Río Bueno|
Puerto Montt|Calbuco|Cochamó|Fresia|Frutillar|Los Muermos|Llanquihue|Maullín|Puerto Varas|Castro|
Ancud|Chonchi|Curaco de Vélez|Dalcahue|Puqueldón|Queilén|Quellón|Quemchi|Quinchao|Achao|Osorno|
Puerto Octay|Purranque|Puyehue|Entre Lagos|Río Negro|San Juan de la Costa|San Pablo|Chaitén|Futaleufú|
Hualaihué|Palena|Chiloé|
Coyhaique|Coihaique|Lago Verde|Aysén|Aisén|Puerto Aysén|Cisnes|Puerto Cisnes|Guaitecas|Cochrane|
O'Higgins|Villa O'Higgins|Tortel|Caleta Tortel|Chile Chico|Río Ibáñez|
Punta Arenas|Laguna Blanca|Río Verde|San Gregorio|Cabo de Hornos|Puerto Williams|Antártica|Porvenir|
Primavera|Timaukel|Natales|Puerto Natales|Torres del Paine
"""

REGIONES = """
Arica y Parinacota|Tarapacá|Atacama|Valparaíso|Metropolitana|Región Metropolitana|
Región Metropolitana de Santiago|Libertador General Bernardo O'Higgins|O'Higgins|Maule|Ñuble|Biobío|
Bío Bío|Bío-Bío|Araucanía|La Araucanía|Los Ríos|Los Lagos|Aysén del General Carlos Ibáñez del Campo|
Magallanes|Magallanes y de la Antártica Chilena|Gran Santiago|Gran Valparaíso|Gran Concepción|
Norte Grande|Norte Chico|Zona Central|Zona Sur|Zona Austral|Patagonia|Isla de Chiloé|Isla Grande de Chiloé|
Cordillera|Maipo|Chacabuco|Talagante|Melipilla|Cachapoal|Colchagua|Cardenal Caro|Elqui|Limarí|Choapa|
Llanquihue|Ranco|Malleco|Cautín
"""

PAISES = """
Chile|Argentina|Perú|Bolivia|Brasil|Uruguay|Paraguay|Ecuador|Colombia|Venezuela|México|Panamá|
Costa Rica|Cuba|Guatemala|Honduras|El Salvador|Nicaragua|República Dominicana|Puerto Rico|Haití|
Estados Unidos|EE.UU.|EEUU|USA|Canadá|España|Portugal|Francia|Italia|Alemania|Reino Unido|Inglaterra|
Irlanda|Países Bajos|Holanda|Bélgica|Suiza|Austria|Suecia|Noruega|Dinamarca|Finlandia|Polonia|
Rusia|Ucrania|Grecia|Turquía|China|Japón|Corea|Corea del Sur|India|Australia|Nueva Zelanda|
Israel|Sudáfrica|Marruecos|Egipto|América|Sudamérica|Latinoamérica|América Latina|Europa|Asia|
África|Oceanía|Unión Europea
"""

# Prefijos que pueden acompañar al nombre ("comuna de Providencia").
PREFIJOS = (
    "comuna de ", "comuna ", "ciudad de ", "ciudad ", "región de ", "región del ", "región ",
    "provincia de ", "provincia del ", "provincia ", "república de ", "república del ",
    "localidad de ", "sector ", "isla de ", "isla ",
)


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().replace("’", "'").split())


def _cargar(*bloques):
    nombres = set()
    for bloque in bloques:
        for n in bloque.replace("\n", "").split("|"):
            n = n.strip()
            if n:
                nombres.add(normalizar(n))
    return nombres


LUGARES_PROTEGIDOS = _cargar(COMUNAS, REGIONES, PAISES)


def es_lugar_protegido(texto: str) -> bool:
    t = normalizar(texto).strip(" .,;:()")
    if t in LUGARES_PROTEGIDOS:
        return True
    for p in PREFIJOS:
        if t.startswith(p) and t[len(p):] in LUGARES_PROTEGIDOS:
            return True
    return False
