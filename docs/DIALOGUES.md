# Sistema de Diálogos

Guiones y árboles de conversación para NPCs importantes.

## 1. Aldea Inicial
### NPC: Anciano del Pueblo (Bienvenida)
- **Estado Inicial:** "Saludos, viajero. Veo que sobreviviste al bosque. Pocos tienen esa suerte."
    - **Opción A:** "¿Quién eres tú?" -> "Soy el guardián de este asentamiento. Llevamos años resistiendo la oscuridad."
    - **Opción B:** "¿Dónde estoy?" -> "Estás en el Valle de los Ecos. Al norte están las minas, al sur el gran desierto."
    - **Opción C:** (Salir) "Tengo prisa." -> "Que los dioses te guíen."

### NPC: Comerciante (Tienda)
- **Saludo:** "¿Buscas equipo? Tengo lo mejor... que se puede encontrar por aquí."
    - **Opción A:** (Comerciar) [Abre interfaz de tienda]
    - **Opción B:** "¿Algún rumor?" -> "Dicen que vieron luces extrañas en la vieja torre anoche."

## 2. Eventos Dinámicos
### Encuentro con Bandido
- **Texto:** "¡Alto ahí! La bolsa o la vida."
    - **Opción A:** (Intimidar - Requiere Fuerza 15) "Apártate o te haré pedazos."
        - Éxito: "¡Está bien, está bien! ¡No me hagas daño!" (El bandido huye).
        - Fallo: "¡Ja! ¡Inténtalo!" (Inicia Combate).
    - **Opción B:** (Pagar 10 monedas) "Toma, es todo lo que tengo."
    - **Opción C:** (Atacar) [Inicia Combate instantáneo].
