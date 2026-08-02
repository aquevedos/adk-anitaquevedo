# Guía de Storytelling y Presentación Comercial: CalzaIntel para Price Shoes 📊👟

Esta guía detalla el enfoque estratégico, el storytelling de negocio y el guion técnico paso a paso para vender la solución **CalzaIntel** a los directores de Compras, Abastecimiento e Innovación de **Price Shoes**.

---

## 💡 El Storytelling: El Desafío del Retail de Moda

### 1. El Gancho (La Pérdida en Inventarios)
*“En el retail tradicional de calzado, cada talla y modelo es una apuesta. Si compramos de más, el dinero se congela en bodegas y se pierde margen con ofertas desesperadas de liquidación. Si compramos de menos, el cliente entra a la tienda, no encuentra su calzado y compra en la competencia. Esto es la **Venta Perdida (Lost Sale)**, el enemigo silencioso del retail.”*

### 2. El Conflicto (La Estacionalidad y el Caos de Contenido)
*“Price Shoes maneja miles de referencias sujetas a **estacionalidades cruzadas extremas**. Las sandalias explotan en verano y mueren en invierno; las botas hacen exactamente lo contrario. Esto llevó a quiebres de stock severos. Pero no solo es el inventario: **crear catálogos para 80,000 SKUs** y procesar manualmente miles de fotos enviadas por cientos de proveedores diferentes colapsa a los equipos creativos y retrasa la salida al mercado de nuevas colecciones.”*

### 3. La Resolución (CalzaIntel + Agente Creativo)
*“CalzaIntel elimina la adivinación y el cuello de botella creativo. Combina la analítica predictiva de **BigQuery ML** para el inventario, con la potencia **multimodal de Gemini 2.5** para procesar fotos de calzado al instante: escribe el copywriting de moda, determina la clasificación arancelaria y realiza una auditoría automatizada de control de calidad sobre las fotos recibidas.”*

---

## 🖥️ Guion de Demostración Paso a Paso (Puntos WOW)

Usa este guion cronológico durante la presentación en vivo del sistema.

### Fase 1: La Narrativa Visual (El Dashboard)
1. **Muestra el Storytelling Slider (Encabezado)**:
   * **Qué decir**: *“Lo primero que ve un gerente al ingresar es la historia de su inventario. El sistema le recuerda visualmente los capítulos críticos: el comportamiento cruzado de Sandalias vs. Botas, las alertas rojas de los stock-outs del año pasado y la fórmula analítica que estamos aplicando para resolverlo.”*
2. **Interactúa con la Tabla y el Gráfico de Proyección**:
   * **Acción**: Haz clic en un producto crítico (ej. **Botín Gamuza Café - BOO-002**).
   * **Qué decir**: *“Al seleccionar cualquier producto, el sistema realiza una consulta en tiempo real a BigQuery. En el gráfico vemos el historial real en morado y la proyección ARIMA inteligente en cyan a 30 días, protegida por un intervalo de confianza. Esto nos dice exactamente cuál es el piso y el techo de la demanda esperada.”*

---

### Fase 2: Módulos Avanzados (Simulación y Precios)
1. **Simulación de Campaña (Hot Sale / Buen Fin)**:
   * **Acción**: Ve a la pestaña **"Simulador de Promociones"**, selecciona *Sneakers*, escribe *40* en incremento de ventas y haz clic en **"Ejecutar Simulación"**.
   * **Qué decir**: *“Miren el gráfico. El modelo ARIMA proyecta la demanda normal, pero al simular un incremento del 40%, el sistema recalcula la curva de demanda (línea naranja) y nos dice cuántas piezas adicionales comprar y el costo estimado. Esto alinea a Marketing con Compras en segundos.”*
2. **Optimización de Precios**:
   * **Acción**: Cambia a la pestaña **"Optimización de Precios"**.
   * **Qué decir**: *“Aqui el sistema actúa como estratega financiero. Si detecta exceso de inventario obsoleto (>90 días de cobertura), sugiere descuentos automáticos de liquidación. Si detecta un producto de alta rotación con pocas piezas (<15 días), sugiere un incremento marginal de precio para maximizar ganancia antes del quiebre de stock.”*

---

### Fase 3: El Agente Creativo (Multimodalidad y Catalogación)
1. **Cargar Imagen del Calzado**:
   * **Acción**: Cambia a la pestaña **"Agente Creativo (Catálogos)"**. Arrastra o selecciona una fotografía de un zapato en la zona de dropzone, y haz clic en **"Procesar Foto con IA"**.
   * **Qué decir**: *“Price Shoes recibe miles de fotos de proveedores que deben publicarse rápido. Vamos a subir esta foto de calzado directamente. Gemini 2.5 Flash analizará la imagen en tiempo real.”*
2. **Explicar los Resultados del Análisis**:
   * **Qué decir**: *“Al instante, el Agente realiza dos flujos en paralelo:*
     * **Generación de Contenido**: Escribe un **Copywriting Comercial en español** de moda adaptado a nuestro estilo de catálogo, y estima la **Fracción Arancelaria (HS Code) y arancel** correspondientes para importación.
     * **Copiloto de Retoque**: Audita la calidad de la foto verificando si el fondo fue removido, si la luz es uniforme y si está alineada. Si pasa el control, la aprueba y la guarda en la nube (`gs://priceshoes-catalog-images/...`) de forma automatizada. De lo contrario, indica qué retoques requiere.”*

---

### Fase 4: Cierre Operativo (Chatbot y PO)
1. **Interactúa con el Chatbot CalzaIntel**:
   * **Acción**: Escribe en la consola de chat: `Genera una orden de compra para SAN-001 con 120 unidades y BOO-002 con 80 unidades`
   * **Qué decir**: *“Una vez que el gerente valida las sugerencias de CalzaIntel, simplemente le pide al agente que genere la Orden de Compra. El agente consolida los datos, calcula costos y entrega un CSV oficial listo para enviar al proveedor.”*

---

## 📈 Argumentos de Venta Clave para Price Shoes (Value Props)

1. **Reducción de Ventas Perdidas (Lost Sales)**:
   * Al tener un Stock de Seguridad dinámico calculado con un 90% de confianza, se reducen hasta en un **85%** los quiebres de stock en temporadas pico.
2. **Aceleración del Time-to-Market (Agente Creativo)**:
   * Escribir descripciones de moda para 80,000 SKUs e inspeccionar fotos toma semanas. Con Gemini, Price Shoes puede catalogar y publicar nuevos modelos en **minutos**, superando a la competencia.
3. **Auditoría de Proveedores y Portal Automatizado**:
   * Filtrar fotos con mala calidad de retoque en la entrada del portal de proveedores ahorra cientos de horas de edición al equipo de diseño interno y garantiza la consistencia visual del catálogo final.


Pipeline BQ: une la tablas que estan en price_Shoes_Test y dame una tabla final contactenada
