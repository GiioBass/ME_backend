# Documento de Diseño del Juego (Game Design Document)

## 1. Concepto General
*   **Género:** RPG de Aventura y Supervivencia (Text-based / MUD style modernizado).
*   **Inspiración:** Mecánicas de exploración y "vibra" de Minecraft, profundidad de WoW/D&D, elementos de LoL.
*   **Estilo Visual:** Inicialmente solo texto (comandos y respuestas). Futuro: Interfaz gráfica Web/Móvil (React/Vite).
*   **Core Loop:** Explorar -> Combatir/Recolectar -> Craftear/Mejorar -> Explorar más lejos/profundo.

## 2. Mundo y Exploración
*   **Generación Procedural:**
    *   El mundo se genera dinámicamente ("Chunk" by "Chunk" o por áreas).
    *   **Áreas Estáticas:** Lugares persistentes y seguros (Casa del jugador, Aldeas, Plantaciones).
    *   **Áreas Dinámicas:** Mazmorras (Dungeons), Templos, Bosques peligrosos. Se regeneran o son instancias únicas para aportar dificultad y novedad.
*   **Biomas y Dimensiones:**
    *   Planeado tener diferentes dimensiones (como Nether/End en Minecraft).
    *   Variedad de terrenos (Pueblos, Templos, Mazmorras).

## 3. Jugador y Progresión
*   **Objetivos:** Sobrevivir, explorar, completar misiones, subir de nivel.
*   **Progresión:** Sistema de niveles y experiencia (XP). Al subir de nivel, los enemigos también se vuelven más fuertes (Scaling).
*   **Facciones/Civilizaciones:** Posibilidad de elegir origen o afiliación.

## 4. Interacción y Mecánicas
*   **Input:** Comandos de texto / Botones de decisión en UI futura.
*   **Inventario:** Gestión de recursos.
    *   **Herramientas:** Para interactuar con el mundo (minar, cortar, etc.).
    *   **Combate:** Armas y armaduras.
    *   **Magia:** Pociones y hechizos.
*   **NPCs:** Interacción pacífica (Aldeanos con profesiones para tradeo) y hostil (Enemigos).

## 5. Combate y Desafíos
*   **Estilo:** Estratégico. El jugador equipa y prepara al personaje.
*   **Automatización:** La exploración puede ser semi-automática, pero las decisiones críticas (pelear vs huir, tomar objeto) son del jugador.
*   **Enemigos:**
    *   Mobs de mundo abierto.
    *   Jefes de mazmorra.
    *   Niveles de dificultad: Bajo, Medio, Alto.

## 6. Economía
*   **Recursos:** Gestión de salud, energía/mana, materiales de crafteo.
*   **Comercio:** Trueque con NPCs (Aldeanos), similar a Minecraft.
*   **Futuro Multiplayer:** Economía entre jugadores.

## 7. Multijugador (Fase Futura)
*   **Tipo:** PvE Cooperativo (No PvP).
*   **Interacción:** Chat interno, comercio, grupos para mazmorras (Raids/Parties).
*   **Persistencia:** Mundo compartido o instancias privadas.

## 8. Recomendaciones Técnicas y de Diseño (Agregadas por el Asistente)

### Arquitectura Hexagonal y API
*   **API-First Design:** Dado que el frontend será separado (React/Vite), el backend no debe devolver "cadenas de texto formateadas para consola", sino **Objetos de Estructura de Datos (JSON)**.
    *   *Incorrecto:* `return "Te encuentras frente a una puerta oxidada."`
    *   *Correcto:* `return { type: "LOC_DESCRIPTION", text: "Te encuentras frente a una puerta oxidada.", interactables: ["puerta"], exits: ["norte"] }`
    *   Esto permite que el Frontend decida si muestra el texto, o si dibuja una puerta en pantalla.

### Sistema de Eventos (Event-Driven)
*   Para lograr la sensación de "mundo vivo" (cultivos creciendo, hornos cocinando mientras no estás), se recomienda un sistema de eventos basado en tiempo o "ticks".
*   Cuando el jugador regresa a un área estática, se calcula el "tiempo delta" desde la última visita para actualizar el estado (ej: cultivo parpadea de 'semilla' a 'trigo').

### Persistencia y Estado
*   **Base de Datos:** Para un RPG con inventarios complejos y mundo persistente, una base de datos relacional (PostgreSQL/SQLite) para datos críticos (jugador, inventario) combinada con una NoSQL o JSON-blob para la generación procedural del mundo (chunks de terreno) suele ser efectiva.

### Mecánica de "Idle" vs "Active"
*   Mencionaste que el personaje "inicie a explorar automáticamente". Esto sugiere mecánicas de **Idle Game** o **Zero Player Game** para el grind, reservando la atención del jugador para momentos clave (Bosses, Loot importante).
*   *Recomendación:* Definir claramente qué acciones consumen "Energía/Tiempo" real y cuáles son instantáneas.
pueden tener dos desiciones, automatico o el jugador decide que hacer. en las fases de exploración de recursos, el jugador puede decidir si explorar o no, si explorar, el personaje explorara automaticamente, si no, el jugador puede decidir que hacer. en las fases de combate, el jugador puede decidir si combatir o huir, si combatir, el personaje combatira automaticamente, pero antes de combatir el jugador debe equipar al personaje y para luego poder tomar desiciones, si no, el jugador puede decidir que hacer.

### Sistema de Entidad-Componente (ECS) - Opcional
*   Considerar un diseño composicional para los items y enemigos.
    *   En lugar de `class EspadaFuego extends Espada`, usar `Item(Components: [Damage(5), FireEffect(2), Name("Espada de Fuego")])`. Esto da mucha flexibilidad para crear items procedurally.
