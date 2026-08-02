// PRICE SHOES - INTERACTIVE DASHBOARD JAVASCRIPT

document.addEventListener("DOMContentLoaded", () => {
    // ----------------------------------------
    // VARIABLES GLOBALES E INICIALIZACIÓN
    // ----------------------------------------
    const sessionId = "session_" + Math.random().toString(36).substring(2, 9);
    let demandChart = null;
    let currentSelectedProduct = null;
    
    let currentProductHistory = null;
    let currentProductForecast = null;
    let currentProductCategory = null;
    
    let activeSimulation = null; // { category, lift }

    // Elementos del DOM
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const clearChatBtn = document.getElementById("clear-chat-btn");
    const catalogTableBody = document.querySelector("#catalog-table tbody");
    
    const metricTotal = document.getElementById("metric-total-products");
    const metricCritical = document.getElementById("metric-critical-products");
    
    const chartTitle = document.getElementById("chart-product-title");
    const chartSubtitle = document.getElementById("chart-product-subtitle");
    const chartBadge = document.getElementById("chart-product-badge");
    const legendPromo = document.getElementById("legend-promo");

    // Elementos de Módulos Avanzados
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const pricingTableBody = document.querySelector("#pricing-table tbody");
    
    const btnRunSim = document.getElementById("btn-run-simulation");
    const promoCategorySelect = document.getElementById("promo-category");
    const promoLiftInput = document.getElementById("promo-lift");
    
    const simExtraQty = document.getElementById("sim-extra-qty");
    const simExtraCost = document.getElementById("sim-extra-cost");
    const simulationTableBody = document.querySelector("#simulation-table tbody");

    // Inicializar todo
    initStorytellingSlider();
    initTabEvents();
    loadDashboardData();
    loadPricingRecommendations();
    setupChatEvents();
    setupSimulationEvents();
    setupCreativeAgentEvents();

    // ----------------------------------------
    // 1. STORYTELLING SLIDER
    // ----------------------------------------
    function initStorytellingSlider() {
        const slides = document.querySelectorAll(".story-slide");
        const dots = document.querySelectorAll(".slider-dots .dot");
        const prevBtn = document.getElementById("prev-story");
        const nextBtn = document.getElementById("next-story");
        let currentSlide = 0;

        function showSlide(index) {
            slides.forEach(s => s.classList.remove("active"));
            dots.forEach(d => d.classList.remove("active"));

            currentSlide = (index + slides.length) % slides.length;
            slides[currentSlide].classList.add("active");
            dots[currentSlide].classList.add("active");
        }

        prevBtn.addEventListener("click", () => showSlide(currentSlide - 1));
        nextBtn.addEventListener("click", () => showSlide(currentSlide + 1));

        dots.forEach(dot => {
            dot.addEventListener("click", (e) => {
                const idx = parseInt(e.target.getAttribute("data-slide"));
                showSlide(idx);
            });
        });
    }

    // ----------------------------------------
    // 2. CONTROL DE PESTAÑAS (TABS)
    // ----------------------------------------
    function initTabEvents() {
        tabButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                tabButtons.forEach(b => b.classList.remove("active"));
                tabPanes.forEach(p => p.classList.remove("active"));
                
                btn.classList.add("active");
                const targetTab = btn.getAttribute("data-tab");
                document.getElementById(targetTab).classList.add("active");
            });
        });
    }

    // ----------------------------------------
    // 3. CARGA DE DATOS DEL DASHBOARD
    // ----------------------------------------
    async function loadDashboardData() {
        try {
            const response = await fetch("/api/inventory-analysis");
            if (!response.ok) throw new Error("Error al obtener datos del inventario");
            const data = await response.json();
            
            if (data.status === "success" && data.analisis.length > 0) {
                renderCatalogTable(data.analisis);
                updateMetricCards(data.analisis);
                
                const firstRow = catalogTableBody.querySelector("tr");
                if (firstRow) {
                    firstRow.click();
                }
            } else {
                catalogTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">No hay datos en la base de datos. Ejecuta la simulación.</td></tr>`;
            }
        } catch (error) {
            console.error(error);
            catalogTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--status-critical);">Error al conectar con BigQuery.</td></tr>`;
        }
    }

    function updateMetricCards(analisis) {
        metricTotal.textContent = analisis.length;
        const criticalCount = analisis.filter(item => item.priority === "CRITICAL" || item.priority === "HIGH").length;
        metricCritical.textContent = criticalCount;
    }

    function renderCatalogTable(analisis) {
        catalogTableBody.innerHTML = "";
        
        analisis.forEach(item => {
            const tr = document.createElement("tr");
            tr.setAttribute("data-id", item.product_id);
            
            let badgeClass = item.priority.toLowerCase();
            let statusText = item.priority;
            if (item.priority === "CRITICAL") statusText = "CRÍTICO";
            if (item.priority === "HIGH") statusText = "ALTO";
            if (item.priority === "MEDIUM") statusText = "MEDIO";
            if (item.priority === "LOW") statusText = "BAJO";

            tr.innerHTML = `
                <td><strong>${item.product_id}</strong></td>
                <td>${item.product_name}</td>
                <td><span class="badge">${item.category}</span></td>
                <td>${item.current_stock} pzas</td>
                <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
            `;
            
            tr.addEventListener("click", () => {
                document.querySelectorAll("#catalog-table tbody tr").forEach(r => r.classList.remove("selected"));
                tr.classList.add("selected");
                currentSelectedProduct = item.product_id;
                currentProductCategory = item.category;
                loadProductForecast(item.product_id, item.product_name, item.priority);
            });
            
            catalogTableBody.appendChild(tr);
        });
    }

    // ----------------------------------------
    // 4. PESTAÑA OPTIMIZACIÓN DE PRECIOS
    // ----------------------------------------
    async function loadPricingRecommendations() {
        try {
            pricingTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 15px;">Calculando optimización...</td></tr>`;
            const response = await fetch("/api/pricing-optimization");
            if (!response.ok) throw new Error("Error al obtener optimización de precios");
            const data = await response.json();
            
            pricingTableBody.innerHTML = "";
            data.forEach(item => {
                const tr = document.createElement("tr");
                
                let actionClass = "mantener";
                if (item.action.includes("DESCUENTO")) actionClass = "liquidar";
                if (item.action.includes("INCREMENTO")) actionClass = "incrementar";
                
                tr.innerHTML = `
                    <td><strong>${item.id}</strong></td>
                    <td>${item.name}</td>
                    <td>$${item.current_price.toFixed(2)} MXN</td>
                    <td><strong style="color: var(--accent-cyan)">$${item.new_price.toFixed(2)} MXN</strong></td>
                    <td><span class="pricing-action ${actionClass}">${item.action}</span></td>
                    <td style="font-size: 0.75rem; color: var(--text-secondary)">${item.reason}</td>
                `;
                pricingTableBody.appendChild(tr);
            });
        } catch (error) {
            console.error(error);
            pricingTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--status-critical);">Error al cargar sugerencias de precios.</td></tr>`;
        }
    }

    // ----------------------------------------
    // 5. PESTAÑA SIMULADOR DE PROMOCIONES
    // ----------------------------------------
    function setupSimulationEvents() {
        btnRunSim.addEventListener("click", runPromotionSimulation);
    }

    async function runPromotionSimulation() {
        const category = promoCategorySelect.value;
        const lift = parseFloat(promoLiftInput.value);
        
        if (isNaN(lift) || lift <= 0) {
            alert("Por favor ingresa un porcentaje de incremento válido.");
            return;
        }

        btnRunSim.disabled = true;
        btnRunSim.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Simulado...`;
        simulationTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 15px;">Corriendo simulación ARIMA en BigQuery...</td></tr>`;

        try {
            const response = await fetch(`/api/simulate-promotion?category=${category}&sales_lift_pct=${lift}`);
            if (!response.ok) throw new Error("Error en simulación");
            const data = await response.json();

            if (data.status === "success") {
                simExtraQty.textContent = `${data.resumen.total_unidades_adicionales} pzas`;
                simExtraCost.textContent = `$${data.resumen.costo_adquisicion_estimado_mxn.toLocaleString("es-MX", {minimumFractionDigits: 2})} MXN`;

                simulationTableBody.innerHTML = "";
                data.detalles.forEach(item => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${item.product_id}</strong></td>
                        <td>${item.product_name}</td>
                        <td>${item.current_stock} pzas</td>
                        <td>${item.normal_forecast_30d} pzas</td>
                        <td><strong style="color: #f97316;">${item.promotional_forecast_30d} pzas</strong></td>
                        <td><span class="status-badge ${item.extra_stock_required > 0 ? 'critical' : 'low'}">${item.extra_stock_required} pzas</span></td>
                    `;
                    simulationTableBody.appendChild(tr);
                });

                activeSimulation = { category: category, lift: lift };
                
                if (currentProductCategory === category) {
                    renderChart(currentProductHistory, currentProductForecast);
                } else {
                    alert(`¡Simulación lista para la categoría ${category}! Selecciona un producto de esta categoría en la lista superior para visualizar la curva de demanda promocional.`);
                }
            }
        } catch (error) {
            console.error(error);
            simulationTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--status-critical);">Error al simular promoción.</td></tr>`;
        } finally {
            btnRunSim.disabled = false;
            btnRunSim.innerHTML = `<i class="fa-solid fa-play"></i> Ejecutar Simulación`;
        }
    }

    // ----------------------------------------
    // 6. CONTROL Y RENDERING DEL GRÁFICO
    // ----------------------------------------
    async function loadProductForecast(productId, productName, priority) {
        try {
            chartTitle.textContent = productName;
            chartSubtitle.textContent = `Cargando pronóstico para ${productId}...`;
            
            let badgeClass = priority.toLowerCase();
            chartBadge.className = `status-badge ${badgeClass}`;
            chartBadge.textContent = priority === "CRITICAL" ? "CRÍTICO" : priority;

            const response = await fetch(`/api/forecast/${productId}`);
            if (!response.ok) throw new Error("Error al obtener forecast");
            const data = await response.json();
            
            if (data.status === "success") {
                chartSubtitle.textContent = `ID: ${productId} | Historial de 60 días + 30 días de Pronóstico ARIMA`;
                
                currentProductHistory = data.historial;
                currentProductForecast = data.pronostico;
                
                renderChart(data.historial, data.pronostico);
            }
        } catch (error) {
            console.error(error);
            chartSubtitle.textContent = "Error al cargar la información del forecast.";
        }
    }

    function renderChart(historial, pronostico) {
        const ctx = document.getElementById("demandChart").getContext("2d");
        
        const historyLabels = historial.map(h => h.date);
        const historySales = historial.map(h => h.sales);
        
        const forecastLabels = pronostico.map(p => p.date);
        const forecastValues = pronostico.map(p => p.forecast);
        const lowerBounds = pronostico.map(p => p.lower_bound);
        const upperBounds = pronostico.map(p => p.upper_bound);
        
        const allLabels = [...historyLabels, ...forecastLabels];
        const historyDataset = [...historySales, ...Array(forecastValues.length).fill(null)];
        const lastHistoryVal = historySales[historySales.length - 1];
        const forecastDataset = [...Array(historySales.length - 1).fill(null), lastHistoryVal, ...forecastValues];
        
        const upperDataset = [...Array(historySales.length - 1).fill(null), lastHistoryVal, ...upperBounds];
        const lowerDataset = [...Array(historySales.length - 1).fill(null), lastHistoryVal, ...lowerBounds];

        const datasets = [
            {
                label: "Ventas Históricas",
                data: historyDataset,
                borderColor: "#8b5cf6",
                borderWidth: 2.5,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: false,
                tension: 0.2
            },
            {
                label: "Pronóstico ARIMA",
                data: forecastDataset,
                borderColor: "#06b6d4",
                borderWidth: 2.5,
                borderDash: [5, 5],
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: false,
                tension: 0.2
            },
            {
                label: "Intervalo Superior",
                data: upperDataset,
                borderColor: "rgba(6, 182, 212, 0.15)",
                borderWidth: 0,
                pointRadius: 0,
                fill: false
            },
            {
                label: "Intervalo de Confianza",
                data: lowerDataset,
                borderColor: "rgba(6, 182, 212, 0.15)",
                borderWidth: 0,
                pointRadius: 0,
                fill: "-1",
                backgroundColor: "rgba(6, 182, 212, 0.06)"
            }
        ];

        if (activeSimulation && activeSimulation.category === currentProductCategory) {
            const promoValues = forecastValues.map(v => v * (1 + activeSimulation.lift/100));
            const promoDataset = [...Array(historySales.length - 1).fill(null), lastHistoryVal, ...promoValues];
            
            datasets.push({
                label: `Pronóstico Promocional (+${activeSimulation.lift}%)`,
                data: promoDataset,
                borderColor: "#f97316",
                borderWidth: 2.5,
                borderDash: [2, 2],
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: false,
                tension: 0.2
            });
            
            legendPromo.style.display = "flex";
            legendPromo.querySelector("span").textContent = `Proyección Promo (+${activeSimulation.lift}%)`;
        } else {
            legendPromo.style.display = "none";
        }

        if (demandChart) {
            demandChart.destroy();
        }

        demandChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: allLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: "index",
                        intersect: false,
                        backgroundColor: "rgba(11, 13, 19, 0.95)",
                        titleColor: "#fff",
                        bodyColor: "#ccc",
                        borderColor: "rgba(255,255,255,0.1)",
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { size: 9 },
                            maxTicksLimit: 12
                        }
                    },
                    y: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" },
                        ticks: {
                            color: "#9ca3af",
                            font: { size: 9 }
                        }
                    }
                }
            }
        });
    }

    // ----------------------------------------
    // 7. PESTAÑA AGENTE CREATIVO (MULTIMODAL)
    // ----------------------------------------
    function setupCreativeAgentEvents() {
        const uploadZone = document.getElementById("upload-zone");
        const fileInput = document.getElementById("image-upload-input");
        const previewContainer = document.getElementById("preview-container");
        const imagePreview = document.getElementById("image-preview");
        const btnRemoveImg = document.getElementById("btn-remove-img");
        const btnProcessImg = document.getElementById("btn-process-image");
        
        const creativeLoading = document.getElementById("creative-loading");
        const creativePlaceholder = document.getElementById("creative-results-placeholder");
        const creativeResultsContent = document.getElementById("creative-results-content");
        
        const resCopywriting = document.getElementById("res-copywriting");
        const resHsCode = document.getElementById("res-hs-code");
        const resTariffRate = document.getElementById("res-tariff-rate");
        
        const checkBg = document.getElementById("check-bg");
        const checkLight = document.getElementById("check-light");
        const checkCenter = document.getElementById("check-center");
        
        const resImageScore = document.getElementById("res-image-score");
        const resApprovalStatus = document.getElementById("res-approval-status");
        const resCloudPath = document.getElementById("res-cloud-path");
        
        let selectedFile = null;

        uploadZone.addEventListener("click", () => {
            fileInput.click();
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleSelectedFile(e.target.files[0]);
            }
        });

        ["dragenter", "dragover"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadZone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                uploadZone.classList.remove("dragover");
            }, false);
        });

        uploadZone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                handleSelectedFile(files[0]);
            }
        });

        function handleSelectedFile(file) {
            if (!file.type.startsWith("image/")) {
                alert("Por favor, selecciona un archivo de imagen válido.");
                return;
            }
            selectedFile = file;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                uploadZone.style.display = "none";
                previewContainer.style.display = "flex";
                btnProcessImg.disabled = false;
            };
            reader.readAsDataURL(file);
        }

        btnRemoveImg.addEventListener("click", () => {
            selectedFile = null;
            fileInput.value = "";
            imagePreview.src = "";
            previewContainer.style.display = "none";
            uploadZone.style.display = "flex";
            btnProcessImg.disabled = true;
            
            creativeResultsContent.style.display = "none";
            creativePlaceholder.style.display = "flex";
        });

        btnProcessImg.addEventListener("click", async () => {
            if (!selectedFile) return;

            btnProcessImg.disabled = true;
            btnRemoveImg.disabled = true;
            
            creativePlaceholder.style.display = "none";
            creativeResultsContent.style.display = "none";
            creativeLoading.style.display = "flex";

            const formData = new FormData();
            formData.append("file", selectedFile);

            try {
                const response = await fetch("/api/analyze-image", {
                    method: "POST",
                    body: formData
                });

                if (!response.ok) throw new Error("Error procesando imagen");
                const data = await response.json();

                resCopywriting.textContent = data.copywriting;
                resHsCode.textContent = data.tariff_hs_code;
                resTariffRate.textContent = data.tariff_rate;
                
                updateChecklistStatus(checkBg, data.retouch_background_removed);
                updateChecklistStatus(checkLight, data.retouch_lighting_ok);
                updateChecklistStatus(checkCenter, data.retouch_centered);
                
                resImageScore.textContent = `${data.image_resolution_score}/10`;
                
                resApprovalStatus.className = "status-badge";
                if (data.status === "APPROVED") {
                    resApprovalStatus.classList.add("low");
                    resApprovalStatus.textContent = "APROBADO";
                } else {
                    resApprovalStatus.classList.add("critical");
                    resApprovalStatus.textContent = "REQUIERE RETOQUE";
                }
                
                resCloudPath.textContent = data.cloud_storage_path;

                creativeLoading.style.display = "none";
                creativeResultsContent.style.display = "block";

            } catch (error) {
                console.error(error);
                alert("Error al procesar la imagen con Gemini. Asegúrate de estar autenticado en Google Cloud.");
                creativeLoading.style.display = "none";
                creativePlaceholder.style.display = "flex";
            } finally {
                btnProcessImg.disabled = false;
                btnRemoveImg.disabled = false;
            }
        });

        function updateChecklistStatus(element, ok) {
            element.className = "fa-solid";
            if (ok) {
                element.classList.add("fa-circle-check", "ok");
            } else {
                element.classList.add("fa-circle-xmark", "fail");
            }
        }
    }

    // ----------------------------------------
    // 8. FLOATING CHAT AGENT (SSE CHAT)
    // ----------------------------------------
    function setupChatEvents() {
        chatSendBtn.addEventListener("click", sendUserMessage);
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendUserMessage();
        });

        clearChatBtn.addEventListener("click", () => {
            chatMessages.innerHTML = `
                <div class="message system-msg">
                    <div class="msg-content">
                        <strong>CalzaIntel:</strong> Historial limpio. ¿En qué puedo ayudarte ahora con tus datos de Price Shoes?
                    </div>
                </div>
            `;
        });
    }

    async function sendUserMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        chatInput.value = "";
        chatInput.disabled = true;
        chatSendBtn.disabled = true;

        appendMessage("user", text);

        const agentMsgDiv = document.createElement("div");
        agentMsgDiv.className = "message agent-msg streaming";
        const contentDiv = document.createElement("div");
        contentDiv.className = "msg-content";
        contentDiv.innerHTML = `<strong>CalzaIntel:</strong> `;
        agentMsgDiv.appendChild(contentDiv);
        chatMessages.appendChild(agentMsgDiv);
        scrollChatToBottom();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, session_id: sessionId })
            });

            if (!response.ok) throw new Error("Error en la conexión del chat");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const formattedChunk = chunk.replace(/\n/g, "<br>");
                contentDiv.innerHTML += formattedChunk;
                scrollChatToBottom();
            }

            agentMsgDiv.classList.remove("streaming");
            
            if (text.toLowerCase().includes("orden") || text.toLowerCase().includes("compra") || text.toLowerCase().includes("precio")) {
                loadPricingRecommendations();
            }

        } catch (error) {
            console.error(error);
            contentDiv.innerHTML += `<span style="color: var(--status-critical);"><br>[Error de conexión: no se pudo obtener respuesta del agente]</span>`;
            agentMsgDiv.classList.remove("streaming");
        } finally {
            chatInput.disabled = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender === "user" ? "user-msg" : "agent-msg"}`;
        
        const contentDiv = document.createElement("div");
        contentDiv.className = "msg-content";
        
        const senderName = sender === "user" ? "Tú" : "CalzaIntel";
        const formattedText = text.replace(/\n/g, "<br>");
        
        contentDiv.innerHTML = `<strong>${senderName}:</strong> ${formattedText}`;
        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);
        scrollChatToBottom();
    }

    function scrollChatToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
