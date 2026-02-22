# Player Commands Reference

Currently supported text commands for the RPG. All commands are case-insensitive.

## Movement
Navigate through the world.

*   `north` / `n`
*   `south` / `s`
*   `east` / `e`
*   `west` / `w`
*   `go [direction]` (e.g., `go north`)
*   `move [direction]`
*   `walk [direction]`
*   `enter`, `down`, `dive` (Enter dungeons/caves)
*   `climb`, `up`, `surface` (Return to surface)

### Combat
*   `attack [enemy]`: Attack an enemy in your current location.
    *   Ejemplo: `attack Goblin` o `attack Spider`
    *   El combate es por turnos automáticos: Tú atacas, y si el enemigo sobrevive, te ataca a ti.

### Tiempo
*   `time`: Muestra la hora y día actual del mundo.
    *   El tiempo avanza solo cuando realizas acciones (Moverse: 10 min, Combatir: 2 min, Recoger: 1 min).
    *   Por la noche (20:00 - 06:00) oscurece.
    *   Regeneras 1 HP cada 10 minutos (ticks) de actividad.you.

## Observation
Inspect your surroundings.

*   `look`
*   `examine`

## Character Information
Check your character's status.

*   `stats`
*   `status`
*   `time`: Check the current day and time (Day/Night cycle).

## Examples
> "go north"
> "look"
> "stats"
