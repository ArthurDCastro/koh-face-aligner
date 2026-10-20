# Tutorial de KOH - Cómo funciona la aplicación

Este tutorial explica, de forma clara, cómo funciona KOH, qué parámetros usa y qué hace cada parte de la interfaz.

> Nota: la aplicación está diseñada para estandarizar retratos detectando la cara principal, centrándola y exportando una imagen final con dimensiones definidas.

## 1. Vista general del flujo

El proceso principal de la app es:

1. recibir una o varias imágenes;
2. localizar la cara más grande presente;
3. ajustar la escala y la posición de la cara dentro de la imagen final;
4. aplicar el tipo de fondo deseado;
5. guardar el resultado en una carpeta de salida.

En palabras simples, el programa intenta transformar cada rostro detectado en una composición estandarizada, manteniendo la cara en el lugar correcto y con proporciones consistentes.

## 2. Qué hace la aplicación por detrás

La lógica principal se divide en varias etapas:

- detección facial con YuNet;
- selección de la cara más grande detectada;
- alineación y redimensionamiento según la proporción facial;
- recorte y posicionamiento en la imagen final;
- eliminación opcional del fondo.

El procesamiento usa OpenCV y, en modo por lotes, la aplicación puede procesar varias fotos de manera secuencial.

## 3. Cómo está organizada la interfaz

La ventana principal tiene estas áreas:

### 3.1 Área de entrada de imágenes

Aquí seleccionas las fotos que se van a procesar.

- botón "Add Images" para archivos individuales;
- botón "Add Folder" para cargar una carpeta completa;
- botón "Clear" para borrar la selección actual;
- lista de archivos para confirmar el lote.

Espacio para imagen ilustrativa:

```md
![Imagen ilustrativa: selección de imágenes en KOH](./images/placeholder-input-images.png)
```

> Inserta aquí una captura de la lista de fotos y los botones de selección.

### 3.2 Configuración de salida

Aquí defines cómo se montará la imagen final:

- Width: ancho final de la imagen en píxeles;
- Height: alto final de la imagen en píxeles;
- Face Ratio: cuánto ocupa la cara en el ancho final;
- Position X: desplazamiento horizontal de la cara;
- Position Y: desplazamiento vertical de la cara;
- Background Removal: tipo de fondo que se aplicará.

Estos parámetros influyen directamente en el resultado visual.

Espacio para imagen ilustrativa:

```md
![Imagen ilustrativa: configuración de salida de KOH](./images/placeholder-output-settings.png)
```

> Inserta aquí una captura o mockup de los campos de configuración.

### 3.3 Carpeta de salida

Elegirás la carpeta donde se guardarán las imágenes procesadas.

La app crea la carpeta automáticamente si no existe y guarda allí los archivos finales.

Espacio para imagen ilustrativa:

```md
![Imagen ilustrativa: selección de la carpeta de salida](./images/placeholder-output-folder.png)
```

> Inserta aquí una imagen del selector de carpeta de destino.

### 3.4 Barra de progreso y estado

Cuando empieza el procesamiento, la interfaz muestra:

- progreso por imagen;
- estado general del procesamiento;
- mensajes de éxito o error;
- el estado actual del lote.

Espacio para imagen ilustrativa:

```md
![Imagen ilustrativa: barra de progreso del procesamiento](./images/placeholder-progress.png)
```

> Inserta aquí una imagen de la barra de progreso mientras se ejecuta el trabajo.

## 4. Qué hace cada característica

### 4.1 Width (ancho)

Define el ancho final de la imagen exportada.

Si es muy estrecha, la cara puede verse comprimida. Si es demasiado ancha, la cara puede parecer pequeña dentro del marco.

### 4.2 Height (alto)

Define la altura final de la imagen.

Afecta el espacio vertical entre la cara y los límites de la imagen, algo esencial para un buen encuadre del retrato.

### 4.3 Face Ratio

Este control define qué proporción de la imagen final ocupa la cara.

Ejemplos:

- valor bajo: la cara ocupa menos espacio;
- valor alto: la cara ocupa más espacio y queda más grande en el cuadro.

En el código, la cara se escala para alcanzar la proporción deseada.

### 4.4 Position X

Define la posición horizontal de la cara dentro de la imagen final.

- 50%: centro horizontal;
- valores menores: cara más a la izquierda;
- valores mayores: cara más a la derecha.

### 4.5 Position Y

Define la posición vertical de la cara.

- 40% es el valor predeterminado, que normalmente deja la cara un poco por encima del centro exacto;
- valores menores: cara más arriba;
- valores mayores: cara más abajo.

### 4.6 Background Removal

La eliminación del fondo puede configurarse en tres modos:

#### Disabled

No se elimina el fondo. El resultado final mantiene el fondo original, pero la cara sigue centrada y redimensionada.

#### Fast

Usa un algoritmo rápido basado en segmentación para aislar al sujeto y quitar el fondo de forma más ligera.

#### AI

Usa MODNet, un modelo de IA especializado en matting de retratos. Este modo suele producir una separación más limpia entre la cara y el fondo, especialmente con iluminación o contraste difíciles.

## 5. Cómo funcionan la detección y el centrado de la cara

La app usa el detector YuNet para encontrar rostros.

### Paso a paso

1. se carga la imagen;
2. el detector busca rostros;
3. se selecciona la cara más grande;
4. se calcula el centro de la cara;
5. la imagen se escala según la proporción configurada;
6. la cara se mueve a la posición X/Y objetivo;
7. se exporta el resultado.

Matemáticamente, el programa aplica una transformación afín para mover y escalar la cara dentro del marco final. Esto mantiene la composición estandarizada aunque la persona aparezca con tamaños o posiciones distintas en la imagen original.

## 6. Qué ocurre con cada imagen procesada

Para cada archivo del lote, la app:

- valida la imagen;
- carga el archivo;
- detecta la cara principal;
- ajusta la composición;
- aplica eliminación de fondo si está configurado;
- guarda la imagen final en la carpeta de salida.

Si no se detecta ninguna cara, el procesamiento se registra como error y el archivo no se guarda.

## 7. Exportación del resultado

Los archivos finales se guardan con nombres como:

- `koh_<nombre-imagen>.jpg` cuando no se elimina el fondo;
- `koh_<nombre-imagen>.png` cuando la eliminación del fondo está activa.

Estos nombres ayudan a identificar rápidamente que la imagen fue procesada por KOH.

## 8. Cómo funciona el procesamiento por lotes

La app puede recibir:

- varias imágenes a la vez;
- una carpeta completa con imágenes;
- una mezcla de archivos y carpetas.

Luego recorre cada elemento de la cola y procesa uno por uno. La barra de progreso se actualiza para mostrar cuánto del lote ya se completó.

Espacio para imagen ilustrativa:

```md
![Imagen ilustrativa: procesamiento por lotes de KOH](./images/placeholder-batch-processing.png)
```

> Inserta aquí una imagen mostrando el procesamiento en secuencia de varias imágenes.

## 9. Consejos para obtener mejores resultados

- usa fotos donde la cara sea claramente visible;
- elige buena iluminación;
- evita rostros parcialmente ocultos;
- prueba Face Ratio y Position Y hasta conseguir el encuadre deseado;
- si el fondo es complejo, el modo AI suele dar resultados más limpios.

## 10. Resumen rápido

KOH es una aplicación para estandarizar retratos y exportar resultados visuales consistentes.

Funciona básicamente así:

- detecta la cara;
- centra y redimensiona la cara en la imagen final;
- ajusta la proporción y la posición;
- elimina el fondo cuando es necesario;
- guarda las imágenes listas para usar.

Si entiendes estos controles, ya puedes usar la app con buenos resultados.

## 11. Siguientes pasos

- prueba con un retrato simple para observar el efecto de Face Ratio;
- modifica Position X y Position Y para cambiar el encuadre;
- compara Disabled, Fast y AI para ver la diferencia en la extracción del fondo;
- prueba un lote completo para evaluar la consistencia del resultado.

---

Si quieres, este tutorial puede ampliarse con:

- guía paso a paso de uso;
- checklist de ajustes según el tipo de retrato;
- ejemplos antes/después para cada modo de fondo.
