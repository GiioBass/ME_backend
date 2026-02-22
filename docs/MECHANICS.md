# Mecánicas del Juego

Reglas fundamentales, fórmulas y lógicas del sistema.

## 1. Combate
*   **Sistema de Turnos:** Al usar el comando `attack`, el jugador golpea primero. Si el enemigo sobrevive, contraataca inmediatamente.
*   **Daño del Jugador:** `Daño = max(1, Fuerza / 2)`.
*   **Daño del Enemigo:** Daño fijo basado en el tipo de enemigo (Ej: Goblin = 2).
*   **Muerte:**
    *   **Enemigo:** Desaparece y otorga XP.
    *   **Jugador:** Reaparece en el inicio con HP restaurado.

## 2. Estados Alterados
- [ ] **Envenenado:** Pierde 5% de HP por turno durante 3 turnos.
- [ ] **Quemado:** Pierde HP fijo por turno, reduce defensa.
- [ ] **Aturdido:** Pierde el próximo turno.
- [ ] **Congelado:** No puede moverse ni atacar, pero gana resistencia física.

## 3. Supervivencia
- [ ] **Hambre:** Barra de 0-100. Al llegar a 0, pierde HP gradualmente. Se reduce al moverse.
- [ ] **Sed:** Similar al hambre, pero baja más rápido en el desierto.
- [ ] **Carga de Peso:** Si supera el límite, movimiento reducido al 50% y no puede correr.

## 4. Progresión
- [ ] **Curva de Experiencia:** `XP_Necesaria = Nivel * 100 * 1.5 ^ (Nivel - 1)`.

## 5. Exploración
*   **Capas Verticales (Z-Layers):**
    *   **Z=0 (Superficie):** Mundo abierto, biomas estándar.
    *   **Z<0 (Subsuelo):** Mazmorras y cuevas. Mayor dificultad, mejores recompensas.
    *   **Z>0 (Cielo):** Posible expansión futura (Islas flotantes).
*   **Generación de Entradas:** Las entradas a cuevas se generan dinámicamente en los chunks de superficie.
