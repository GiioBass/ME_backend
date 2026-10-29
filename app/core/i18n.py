import re
from contextvars import ContextVar
from typing import Dict, Any, List

_current_lang: ContextVar[str] = ContextVar("current_lang", default="en")


def set_current_lang(lang: str) -> None:
    raw = (lang or "en").strip().lower()
    norm = "es" if raw.startswith("es") else "en"
    _current_lang.set(norm)


def get_current_lang() -> str:
    return _current_lang.get()


# Exact & phrase translations for narrative messages, dialogues, items, and descriptions (EN -> ES)
EXACT_TRANSLATIONS_ES: Dict[str, str] = {
    # General & System
    "Please enter a command.": "Por favor ingresa un comando.",
    "Terminal cleared.": "Terminal limpiada.",
    "You are not carrying anything.": "No llevas nada en tu inventario.",
    "Take what?": "¿Tomar qué?",
    "Drop what?": "¿Soltar qué?",
    "Equip what?": "¿Equipar qué?",
    "Unequip from what slot?": "¿Desequipar de qué ranura?",
    "Consume what?": "¿Consumir qué?",
    "Buy what?": "¿Comprar qué?",
    "Sell what?": "¿Vender qué?",
    "Talk to whom?": "¿Hablar con quién?",
    "Store what?": "¿Guardar qué?",
    "Retrieve what?": "¿Retirar qué?",
    "You don't see that here.": "No ves eso aquí.",
    "You don't have that.": "No tienes eso.",
    "You cannot equip that.": "No puedes equipar eso.",
    "Item not found in inventory.": "Objeto no encontrado en el inventario.",
    "Nothing is equipped there.": "No hay nada equipado ahí.",
    "There is no camp chest here.": "No hay ningún cofre de campamento aquí.",
    "The camp chest is empty.": "El cofre del campamento está vacío.",
    "There is no camp chest here to store items.": "No hay cofre de campamento aquí para guardar objetos.",
    "There is no camp chest here to retrieve items from.": "No hay cofre de campamento aquí para retirar objetos.",
    "There is no water source here to fill anything.": "No hay ninguna fuente de agua aquí para llenar algo.",
    "You don't have an Empty Flask to fill.": "No tienes un Frasco Vacío (Empty Flask) para llenar.",
    "There is no water source here to drink from.": "No hay ninguna fuente de agua aquí para beber.",
    "You are not thirsty.": "No tienes sed.",
    "You cup your hands and drink the cool, refreshing water.": "Juntas tus manos y bebes el agua fresca y refrescante.",
    "You are too hungry or thirsty to rest effectively.": "Tienes demasiada hambre o sed para descansar efectivamente.",
    "You are already fully rested.": "Ya estás completamente descansado.",
    "You take a long rest and wake up feeling completely refreshed. Your HP is fully restored.": "Tomas un largo descanso y despiertas completamente renovado. Tu HP se ha restaurado por completo.",
    "It is pitch black. You cannot see anything without a light source.": "Está completamente oscuro. No puedes ver nada sin una fuente de luz.",
    "You are not currently in a conversation with anyone.": "Actualmente no estás conversando con nadie.",
    "The conversation ended.": "La conversación ha terminado.",
    "You are not in a conversation.": "No estás en una conversación.",
    "There is no merchant here to trade with.": "No hay ningún mercader aquí para comerciar.",
    "There is no merchant here to buy from.": "No hay ningún mercader aquí a quien comprarle.",
    "There is no merchant here to sell items to.": "No hay ningún mercader aquí a quien venderle objetos.",

    # Dialogue texts (NPCs)
    "Greetings, traveler. I see you survived the dark woods. Few have such luck.": "Saludos, viajero. Veo que sobreviviste al bosque oscuro. Pocos tienen tanta suerte.",
    "Who are you?": "¿Quién eres?",
    "Where am I?": "¿Dónde estoy?",
    "Do you have any tasks for me?": "¿Tienes alguna misión para mí?",
    "I must get going. Farewell.": "Debo irme. Hasta pronto.",
    "I am the guardian of this settlement. We have resisted the spreading darkness for decades.": "Soy el guardián de este asentamiento. Hemos resistido la oscuridad durante décadas.",
    "Tell me more about this place.": "Cuéntame más sobre este lugar.",
    "May the gods guide you.": "Que los dioses te guíen.",
    "You are in the Echo Valley. To the north lie old abandoned mines; to the south, the scorched desert.": "Estás en el Valle del Eco. Al norte yacen viejas minas abandonadas; al sur, el desierto abrasador.",
    "I have other questions.": "Tengo otras preguntas.",
    "Thank you for the directions.": "Gracias por las indicaciones.",
    "Our settlement needs basic supplies to reinforce the perimeter. Start by gathering wood, crafting an axe and building a campfire.": "Nuestro asentamiento necesita suministros básicos para reforzar el perímetro. Empieza recolectando madera, fabricando un hacha y construyendo una fogata.",
    "I will do it.": "Lo haré.",
    "Looking for gear, traveler? I have the finest wares... that can be found in these barren lands.": "¿Buscas equipo, viajero? Tengo las mejores mercancías... que se pueden encontrar en estas tierras áridas.",
    "Show me what you have for sale.": "Muéstrame qué tienes a la venta.",
    "Heard any interesting rumors?": "¿Has escuchado algún rumor interesante?",
    "Just browsing. Farewell.": "Solo estoy mirando. Hasta luego.",
    "They say strange lights flickered around the dungeon entrance last night. Watch your back down there.": "Dicen que luces extrañas parpadearon cerca de la entrada del calabozo anoche. Cuida tu espalda allá abajo.",
    "Let me look at your goods instead.": "Déjame ver tus mercancías mejor.",
    "Thanks for the warning.": "Gracias por la advertencia.",
    "Take your time. Good steel is worth its weight in gold.": "Tómate tu tiempo. El buen acero vale su peso en oro.",
    "That is all for now.": "Eso es todo por ahora.",
    "Oh, thank goodness someone capable is here! Giant vermin have infested my cellar!": "¡Oh, menos mal que hay alguien capaz aquí! ¡Alimañas gigantes han infestado mi sótano!",
    "What kind of vermin? I can help.": "¿Qué clase de alimañas? Puedo ayudar.",
    "Not my problem, old man.": "No es mi problema, anciano.",
    "Foul cave spiders and giant rats! Slay 3 of them and I'll reward you with gold and fresh apples!": "¡Inmundas arañas de cueva y ratas gigantes! ¡Elimina a 3 de ellas y te recompensaré con oro y manzanas frescas!",
    "Consider it done.": "Considéralo hecho.",

    # Item Descriptions
    "A vial of crimson liquid that rapidly heals wounds.": "Un vial de líquido carmesí que sana heridas rápidamente.",
    "A glowing azure potion that restores mana.": "Una poción azul brillante que restaura el maná.",
    "Nutritious trail food restoring 50 hunger and minor vitality.": "Raciones nutritivas de viaje que restauran 50 de hambre y vitalidad menor.",
    "A flask filled with pure, refreshing spring water.": "Un frasco lleno de agua pura y refrescante de manantial.",
    "An empty glass bottle suitable for carrying water.": "Una botella de vidrio vacía apta para transportar agua.",
    "Sterile cloth wraps to treat bleeding and minor wounds.": "Vendas de tela estéril para tratar sangrado y heridas menores.",
    "A wooden torch to illuminate dark places.": "Una antorcha de madera para iluminar lugares oscuros.",
    "Lightweight blade with swift piercing damage.": "Hoja ligera con rápido daño perforante.",
    "Toughened hide tunic granting reliable physical defense.": "Túnica de cuero endurecido que otorga defensa física confiable.",
    "Soft fleece sheared from sheep or wild beasts, perfect for weaving cloth.": "Lana suave esquilada, ideal para tejer tela.",
    "Woven plant fabric.": "Tela tejida de fibras vegetales.",
    "A block of freshly chopped timber.": "Un bloque de madera recién cortada.",
    "A heavy bar of refined iron metal.": "Un lingote pesado de hierro refinado.",
    "A questionable forest mushroom.": "Un hongo del bosque de aspecto dudoso.",
    "A sweet red berry.": "Una baya roja dulce.",
    "A crunchy wild apple.": "Una manzana silvestre crujiente.",
    "A crisp, delicious red apple.": "Una manzana roja fresca y deliciosa.",
    "Water extracted from a cactus.": "Agua extraída de un cactus.",
    "A crude but sharp knife made of stone and wood.": "Un cuchillo rústico pero afilado hecho de piedra y madera.",
    "A heavy stone axe for chopping or combat.": "Un hacha pesada de piedra para talar o combatir.",
    "A sturdy stone pickaxe for breaking rock and mining.": "Un pico resistente de piedra para romper rocas y minar.",
    "A lethal sharpened blade forged of solid iron.": "Una espada letal forjada en hierro sólido.",
    "An old sword, heavily rusted.": "Una espada vieja y muy oxidada.",
    "A moth-eaten cloth tunic.": "Una túnica de tela desgastada.",
    "A stiff, poorly maintained leather chestpiece.": "Una pechera de cuero rígida y desgastada.",
    "A wooden board that barely resembles a shield.": "Una tabla de madera que apenas parece un escudo.",
    "A heavy, sharp dark blade.": "Una hoja oscura, pesada y afilada.",

    # Command Help Descriptions
    "Move in a cardinal direction (north, south, east, west, up, down).": "Muévete en una dirección cardinal (north, south, east, west, up, down).",
    "Examine your current surroundings, items, NPCs and enemies.": "Examina tus alrededores, objetos, ciudadanos y enemigos.",
    "Check your character's health, mana, gold and attributes.": "Revisa la salud, maná, oro y atributos de tu personaje.",
    "View the items you are currently carrying.": "Observa los objetos que llevas en tu inventario.",
    "Check the current world time and day/night cycle.": "Consulta la hora actual del mundo y el ciclo día/noche.",
    "Display the list of available commands.": "Muestra la lista de comandos disponibles.",
    "Clear the terminal screen.": "Limpia la pantalla de la terminal.",
    "Pick up an item from the ground.": "Recoge un objeto del suelo.",
    "Drop an item from your inventory onto the ground.": "Suelta un objeto de tu inventario al suelo.",
    "Consume food, potions or water to restore stats.": "Consume comida, pociones o agua para restaurar estadísticas.",
    "Fill an empty flask at a water source.": "Llena un frasco vacío en una fuente de agua.",
    "Attack a hostile enemy in your current location.": "Ataca a un enemigo hostil en tu ubicación actual.",
    "Equip a weapon or armor from your inventory.": "Equipa un arma o armadura de tu inventario.",
    "Unequip an item from a specific slot (weapon or armor).": "Desequipa un objeto de una ranura (weapon o armor).",
    "Scan nearby sectors for points of interest and resources.": "Escanea los sectores cercanos en busca de puntos de interés y recursos.",
    "Establish a fast-travel camp and storage chest at your location.": "Establece un campamento de viaje rápido y cofre en tu ubicación.",
    "Fast-travel to a previously established camp waypoint.": "Viaja rápido a un campamento establecido previamente.",
    "Rest to recover HP at the cost of hunger and thirst.": "Descansa para recuperar HP a cambio de hambre y sed.",
    "View items stored in the local camp chest.": "Mira los objetos guardados en el cofre del campamento.",
    "Store an item from your inventory into the camp chest.": "Guarda un objeto de tu inventario en el cofre del campamento.",
    "Retrieve an item from the camp chest into your inventory.": "Retira un objeto del cofre del campamento a tu inventario.",
    "Craft an item using a known recipe and materials.": "Fabrica un objeto usando una receta conocida y materiales.",
    "List all crafting recipes and their required materials.": "Lista todas las recetas de fabricación y sus materiales requeridos.",
    "Start a conversation with an NPC in your location.": "Inicia una conversación con un NPC en tu ubicación.",
    "Select a dialogue option by number or keyword.": "Selecciona una opción de diálogo por número o palabra clave.",
    "Buy an item from a local merchant.": "Compra un objeto a un mercader local.",
    "Sell an item from your inventory to a local merchant.": "Vende un objeto de tu inventario a un mercader local.",
    "View the local merchant's shop inventory and prices.": "Mira el inventario y precios de la tienda del mercader local.",
    "View your active and completed quests.": "Revisa tus misiones activas y completadas.",
    "Turn in a completed quest to claim your reward.": "Entrega una misión completada para reclamar tu recompensa.",
    "View or select your combat class specialization.": "Mira o selecciona tu especialización de clase de combate.",
    "List your unlocked class skills and mana costs.": "Lista tus habilidades de clase desbloqueadas y costos de maná.",
    "Use an active class skill in combat or on yourself.": "Usa una habilidad activa de clase en combate o sobre ti mismo.",
    "Colossal black basalt paws rise from the scorched dunes. At the center of the sunken altar crouches the Black Hound Sphinx, guarding the deep desert.": "Colosales garras de basalto negro se alzan entre las dunas abrasadas. En el centro del altar hundido acecha la Esfinge Perro Negro, custodiando el desierto profundo.",
    "An ancient desert sphinx with the sleek obsidian body of a winged lion and the fierce head of a black jackal-hound. Golden eyes burn beneath its nemes headdress.": "Una antigua esfinge del desierto con cuerpo de obsidiana alado y la feroz cabeza de un perro chacal negro. Sus ojos dorados arden bajo su tocado nemes.",
}

REGEX_TRANSLATIONS_ES = [
    (re.compile(r"^Account registered successfully\. Welcome, (.+)!$"), r"Cuenta registrada exitosamente. ¡Bienvenido, \1!"),
    (re.compile(r"^Authentication verified\. Welcome back, (.+)\.$"), r"Autenticación verificada. Bienvenido de nuevo, \1."),
    (re.compile(r"^Welcome, (.+)! Your adventure begins\.$"), r"¡Bienvenido, \1! Tu aventura comienza."),
    (re.compile(r"^Welcome back, (.+)\.$"), r"Bienvenido de nuevo, \1."),
    (re.compile(r"^You bought (.+) for (\d+) Gold\. \(Remaining Gold: (\d+)g\)$"), r"Compraste \1 por \2 de Oro. (Oro restante: \3g)"),
    (re.compile(r"^You sold (.+) to (.+) for (\d+) Gold\. \(Current Gold: (\d+)g\)$"), r"Vendiste \1 a \2 por \3 de Oro. (Oro actual: \4g)"),
    (re.compile(r"^(.+) does not sell '(.+)'\.$"), r"\1 no vende '\2'."),
    (re.compile(r"^(.+) is out of stock for (.+)\.$"), r"\1 no tiene existencias de \2."),
    (re.compile(r"^You do not have enough gold\. Requires (\d+)g \(You have (\d+)g\)\.$"), r"No tienes suficiente oro. Requiere \1g (Tienes \2g)."),
    (re.compile(r"^You cannot carry (.+), your inventory is full\.$"), r"No puedes cargar \1, tu inventario está lleno."),
    (re.compile(r"^You don't have '(.+)' in your inventory\.$"), r"No tienes '\1' en tu inventario."),
    (re.compile(r"^You don't have a '(.+)' in your inventory\.$"), r"No tienes '\1' en tu inventario."),
    (re.compile(r"^You don't have '(.+)'\.$"), r"No tienes '\1'."),
    (re.compile(r"^You picked up (\d+)x (.+)\."), r"Recogiste \1x \2."),
    (re.compile(r"^You dropped (\d+)x (.+)\."), r"Soltaste \1x \2."),
    (re.compile(r"^You equipped the (.+)\."), r"Equipaste \1."),
    (re.compile(r"^You unequipped the (.+)\."), r"Desequipaste \1."),
    (re.compile(r"^You consumed (.+)\."), r"Consumiste \1."),
    (re.compile(r"Restored (\d+) HP\."), r"Restauró \1 HP."),
    (re.compile(r"Restored (\d+) MP\."), r"Restauró \1 MP."),
    (re.compile(r"Restored (\d+) Hunger\."), r"Restauró \1 de Hambre."),
    (re.compile(r"Restored (\d+) Thirst\."), r"Restauró \1 de Sed."),
    (re.compile(r"You now have an Empty Flask\."), r"Ahora tienes un Frasco Vacío (Empty Flask)."),
    (re.compile(r"^You fill the (.+) with water\."), r"Llenas \1 con agua."),
    (re.compile(r"^You stored (.+) in the camp chest\."), r"Guardaste \1 en el cofre del campamento."),
    (re.compile(r"^You retrieved (.+) from the camp chest\."), r"Retiraste \1 del cofre del campamento."),
    (re.compile(r"^There is no one named '(.+)' here to talk to\.$"), r"No hay nadie llamado '\1' aquí para hablar."),
    (re.compile(r"^\[(.+)\] Farewell\."), r"[\1] Hasta pronto."),
    (re.compile(r"Dialogue Options:"), r"Opciones de Diálogo:"),
    (re.compile(r"You see items: "), r"Ves objetos: "),
    (re.compile(r"Enemies here: "), r"Enemigos aquí: "),
    (re.compile(r"People here: "), r"Personas aquí: "),
    (re.compile(r"\[NIGHT\] "), r"[NOCHE] "),
    (re.compile(r"\(It is dark\)"), r"(Está oscuro)"),
    (re.compile(r"^Unknown command: '(.+)'\. Type 'help' for a list of commands\.$"), r"Comando desconocido: '\1'. Escribe 'help' o 'ayuda' para ver los comandos."),
]


def translate_text(text: str, lang: str = "en") -> str:
    if not text or lang != "es":
        return text

    if text in EXACT_TRANSLATIONS_ES:
        return EXACT_TRANSLATIONS_ES[text]

    # Translate line by line and apply regex patterns
    lines = text.split("\n")
    translated_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped in EXACT_TRANSLATIONS_ES:
            translated_lines.append(line.replace(stripped, EXACT_TRANSLATIONS_ES[stripped]))
            continue

        new_line = line
        for pattern, replacement in REGEX_TRANSLATIONS_ES:
            new_line = pattern.sub(replacement, new_line)
        translated_lines.append(new_line)

    return "\n".join(translated_lines)


def translate_response(resp: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
    if not resp or lang != "es":
        return resp

    if "message" in resp and isinstance(resp["message"], str):
        resp["message"] = translate_text(resp["message"], lang)

    player = resp.get("player")
    if isinstance(player, dict):
        dlg = player.get("active_dialogue")
        if isinstance(dlg, dict):
            if "text" in dlg and isinstance(dlg["text"], str):
                dlg["text"] = translate_text(dlg["text"], lang)
            if "options" in dlg and isinstance(dlg["options"], list):
                for opt in dlg["options"]:
                    if isinstance(opt, dict) and "text" in opt:
                        opt["text"] = translate_text(opt["text"], lang)

    location = resp.get("location")
    if isinstance(location, dict):
        if "description" in location and isinstance(location["description"], str):
            location["description"] = translate_text(location["description"], lang)
        shop = location.get("shop")
        if isinstance(shop, dict):
            if shop.get("merchant_title") == "Traveling Trader":
                shop["merchant_title"] = "Comerciante Viajero"
            elif shop.get("merchant_title") == "Market Outpost":
                shop["merchant_title"] = "Puesto de Mercado"
            for item in shop.get("items", []):
                if isinstance(item, dict) and "description" in item:
                    item["description"] = translate_text(item["description"], lang)

    return resp


def translate_commands_list(commands: List[Dict[str, Any]], lang: str = "en") -> List[Dict[str, Any]]:
    if not commands or lang != "es":
        return commands

    result = []
    for cmd in commands:
        item = dict(cmd)
        desc = item.get("description", "")
        item["description"] = translate_text(desc, lang)
        result.append(item)
    return result
