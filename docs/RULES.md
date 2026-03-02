# Reglas de Desarrollo (Development Rules)

1. **SOLID y Escalabilidad:** Mantener el código lo más limpio posible usando principios SOLID. Si una funcionalidad, servicio o controlador crece demasiado, **separarlo en endpoints independientes** o extraer la lógica a dominios y utilities nuevos. No concentrar todo en un solo archivo gordo (`Fat Controller`).
2. **Nombres Orientados a Dominio:** Utilizar nombres en inglés para variables, métodos e interfaces para preservar el estándar del código, a pesar de que el contenido textual del juego pueda traducirse.
