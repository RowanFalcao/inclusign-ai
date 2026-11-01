/**
 * IncluSign AI — Lógica do Frontend (SPA)
 * ========================================
 * Navegação, chamadas à API, renderização e interatividade.
 * 
 * Atributos de qualidade aplicados:
 *   - Usabilidade: Feedback visual imediato, loading states, validação
 *   - Confiabilidade: Tratamento de erros em todas as chamadas
 *   - Eficiência: Debounce, lazy loading de dados
 */

(function () {
    'use strict';

    // ========================================================================
    // CONSTANTES
    // ========================================================================
    const API_BASE = '';  // Mesmo servidor (Flask)
    const STATUS_POLL_INTERVAL = 30000;  // 30 segundos

    // ========================================================================
    // STATE
    // ========================================================================
    let currentSection = 'home';
    let sessionId = generateSessionId();
    let activeRequest = null;          // AbortController atual
    let activeModule = null;           // 'traducao' ou 'planejamento' (para Esc saber qual resetar)

    // ========================================================================
    // INICIALIZAÇÃO
    // ========================================================================
    document.addEventListener('DOMContentLoaded', function () {
        initTheme();
        initNavigation();
        initForms();
        initTelemetry();
        checkSystemStatus();
        setInterval(checkSystemStatus, STATUS_POLL_INTERVAL);
    });

    // ========================================================================
    // TEMA (Claro/Escuro)
    // ========================================================================
    function initTheme() {
        var themeToggleBtn = document.getElementById('theme-toggle');
        if (!themeToggleBtn) return;

        // Recuperar preferência salva ou usar escuro como padrão
        var savedTheme = localStorage.getItem('inclusign_theme') || 'dark';
        applyTheme(savedTheme);

        themeToggleBtn.addEventListener('click', function () {
            var currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('inclusign_theme', theme);

        var themeToggleBtn = document.getElementById('theme-toggle');
        if (themeToggleBtn) {
            themeToggleBtn.innerHTML = theme === 'dark' ? '☀️ Modo Claro' : '🌙 Modo Escuro';
        }
    }

    // ========================================================================
    // NAVEGAÇÃO SPA
    // ========================================================================
    function initNavigation() {
        // Botões de navegação
        document.querySelectorAll('.nav-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                navigateTo(this.dataset.section);
            });
        });

        // Cards de agentes (Home)
        var cardTraducao = document.getElementById('card-traducao');
        if (cardTraducao) {
            cardTraducao.addEventListener('click', function () {
                navigateTo('traducao');
            });
            cardTraducao.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigateTo('traducao');
                }
            });
        }

        var cardPlanejamento = document.getElementById('card-planejamento');
        if (cardPlanejamento) {
            cardPlanejamento.addEventListener('click', function () {
                navigateTo('planejamento');
            });
            cardPlanejamento.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigateTo('planejamento');
                }
            });
        }
    }

    function navigateTo(section) {
        currentSection = section;

        // Atualizar botões de navegação
        document.querySelectorAll('.nav-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.section === section);
        });

        // Atualizar seções visíveis
        document.querySelectorAll('.section').forEach(function (sec) {
            sec.classList.toggle('active', sec.id === 'section-' + section);
        });

        // Carregar dados da telemetria quando abrir a seção
        if (section === 'telemetria') {
            loadTelemetry();
        }

        // Scroll suave para o topo
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ========================================================================
    // FORMULÁRIOS
    // ========================================================================
    function initForms() {
        // Form de Tradução
        var formTraducao = document.getElementById('form-traducao');
        if (formTraducao) {
            formTraducao.addEventListener('submit', handleTranslation);
        }

        // Seleção de domínio → exibir aviso de escopo (RF-004)
        var dominio = document.getElementById('dominio');
        if (dominio) {
            dominio.addEventListener('change', handleDominioChange);
        }

        // Form de Planejamento
        var formPlanejamento = document.getElementById('form-planejamento');
        if (formPlanejamento) {
            formPlanejamento.addEventListener('submit', handlePlanning);
        }
    }

    // ========================================================================
    // AVISO DE ESCOPO (RF-004)
    // ========================================================================
    function handleDominioChange() {
        var dominio = this.value;
        var avisoEl = document.getElementById('aviso-escopo');
        var textoEl = document.getElementById('aviso-escopo-texto');

        if (!dominio || !avisoEl || !textoEl) {
            if (avisoEl) avisoEl.style.display = 'none';
            return;
        }

        var avisos = {
            computacao: '<strong>Calibrado para Excelência:</strong> Nossa IA atinge precisão máxima em Programação, Redes, Segurança Cibernética, Algoritmos e Estruturas de Dados. Explore termos destas áreas para obter traduções e apoios semióticos com qualidade superior.',
            medicina: '<strong>Calibrado para Excelência:</strong> Nossa IA atinge precisão máxima em Anatomia e Farmacologia. Explore termos destas áreas para obter traduções e apoios semióticos com qualidade superior.',
            agronomia: '<strong>Calibrado para Excelência:</strong> Nossa IA atinge precisão máxima em Fitossanidade, Mecanização Agrícola, Biotecnologia e Ciência do Solo. Explore termos destas áreas para obter traduções e apoios semióticos com qualidade superior.'
        };

        textoEl.innerHTML = avisos[dominio] || '';
        avisoEl.style.display = dominio ? 'flex' : 'none';
    }

    // ========================================================================
    // TRADUÇÃO CONTEXTUAL (RF-005 a RF-009)
    // ========================================================================
    async function handleTranslation(e) {
        e.preventDefault();

        var dominio = document.getElementById('dominio').value;
        var termo = document.getElementById('termo').value.trim();
        var contexto = document.getElementById('contexto-traducao').value.trim();

        if (!dominio || !termo) {
            showAlert('Por favor, selecione a área e insira o termo técnico.', 'warning');
            return;
        }

        // Mostrar loading inicial
        showLoading('traducao', true);
        showStopButton('traducao');      // Exibe o botão de parar independente
        hideResult('traducao');

        var contentEl = document.getElementById('result-traducao-content');
        if (contentEl) contentEl.innerHTML = ''; // Limpar anterior

        var avisoLimitacaoBox = document.getElementById('aviso-limitacao-traducao');
        if (avisoLimitacaoBox) avisoLimitacaoBox.style.display = 'none';

        var avisoLimitacao = document.querySelector('#aviso-limitacao-traducao span:last-child');
        if (avisoLimitacao) avisoLimitacao.textContent = '';

        var metaEl = document.getElementById('result-traducao-meta');
        if (metaEl) metaEl.innerHTML = '';

        try {
            if (activeRequest) activeRequest.abort();
            activeRequest = new AbortController();
            activeModule = 'traducao';

            var response = await fetch(API_BASE + '/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: activeRequest.signal,  // ← CORREÇÃO: conectar o sinal ao fetch
                body: JSON.stringify({
                    session_id: sessionId,
                    dominio: dominio,
                    termo: termo,
                    contexto: contexto,
                    stream: true // Ativar streaming
                })
            });

            if (!response.ok) {
                throw new Error('Erro na requisição da rede');
            }

            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var partialText = "";
            var isFirstChunk = true;

            var rawText = "";
            var isOllamaNativeThinking = false;
            var nativeThinkingText = "";

            showResult('traducao');
            if (contentEl) {
                contentEl.innerHTML =
                    '<details id="reasoning-details-traducao" style="margin-bottom: 15px; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; background-color: var(--bg-secondary);">' +
                    '<summary id="reasoning-summary-traducao" style="cursor: pointer; font-weight: 600; color: var(--text-muted); list-style-position: inside;">🧠 Processo de raciocínio da IA<span class="jumping-dots"><span>.</span><span>.</span><span>.</span></span></summary>' +
                    '<div id="reasoning-content-traducao" style="color: var(--text-muted); font-style: italic; font-size: 0.9em; margin-top: 10px; white-space: pre-wrap; font-family: monospace; max-height: 150px; overflow-y: auto;"></div>' +
                    '</details>' +
                    '<div id="final-content-traducao"></div>';
            }

            while (true) {
                var { done, value } = await reader.read();
                if (done) break;

                // Remover tela de carregamento no primeiro token
                if (isFirstChunk) {
                    showLoading('traducao', false);
                    // Botão de parar já está visível (exibido antes do fetch)
                    isFirstChunk = false;
                }

                partialText += decoder.decode(value, { stream: true });

                // SSE envia mensagens no formato "data: {JSON}\n\n"
                var parts = partialText.split('\n\n');
                // O último item sempre será um fragmento incompleto, guardamos para a próxima iteração
                partialText = parts.pop() || '';

                for (var i = 0; i < parts.length; i++) {
                    var dataStr = parts[i].replace(/^data:\s*/, '').trim();
                    if (!dataStr) continue;

                    try {
                        var dataObj = JSON.parse(dataStr);

                        if (dataObj.done) {
                            // Fim da stream
                            hideStopButton('traducao');
                            activeRequest = null;
                            activeModule = null;
                            showChatBox('traducao');

                            // Restaurar o aviso de limitação
                            if (avisoLimitacao) {
                                avisoLimitacao.innerHTML = "<strong>AVISO IMPORTANTE:</strong> As sugestões apresentadas são apoios pedagógicos gerados por inteligência artificial e NÃO constituem sinais oficiais da Língua Brasileira de Sinais (Libras). A criação e validação de novos sinais é competência exclusiva da comunidade surda e de linguístas especializados.";
                            }
                            var avisoLimitacaoBox = document.getElementById('aviso-limitacao-traducao');
                            if (avisoLimitacaoBox) avisoLimitacaoBox.style.display = 'flex';

                            // Restaurar os metadados (tempo e tokens)
                            if (metaEl) {
                                var selectDominio = document.getElementById('dominio');
                                var nomeDominio = selectDominio.options[selectDominio.selectedIndex].text;
                                metaEl.innerHTML =
                                    '<span class="result-meta-item">📚 ' + nomeDominio + '</span>' +
                                    '<span class="result-meta-item">🔤 Tokens: ~' + (dataObj.tokens_used || 0) + '</span>' +
                                    '<span class="result-meta-item">⏱️ ' + (dataObj.response_time_ms || 0) + ' ms</span>';
                            }
                            break;
                        }

                        if (!dataObj.success) {
                            hideStopButton('traducao');
                            showError('traducao', dataObj.content || 'Erro ao processar tradução.');
                            break;
                        }

                        var chunkText = dataObj.content || '';

                        if (dataObj.is_thinking) {
                            nativeThinkingText += chunkText;
                        } else {
                            rawText += chunkText;
                            var sum = document.getElementById('reasoning-summary-traducao');
                            if (sum && !sum.dataset.done) {
                                sum.innerHTML = '🧠 Processo de raciocínio da IA';
                                sum.dataset.done = 'true';
                                var detailsBox = document.getElementById('reasoning-details-traducao');
                                if (detailsBox) detailsBox.removeAttribute('open');
                            }
                        }

                        // Remove empty spaces at start
                        var displayFinal = rawText.replace(/^\s+/, '');

                        // Render
                        var rEl = document.getElementById('reasoning-content-traducao');
                        if (rEl && nativeThinkingText.length > 0) {
                            rEl.textContent = nativeThinkingText;
                            rEl.scrollTop = rEl.scrollHeight; // Auto-scroll
                        }

                        var fEl = document.getElementById('final-content-traducao');
                        if (fEl && displayFinal.length > 0) {
                            fEl.innerHTML = formatMarkdown(displayFinal);
                        }

                    } catch (err) {
                        console.warn("Erro ao fazer parse do chunk SSE:", err, dataStr);
                    }
                }
            }

        } catch (error) {
            showLoading('traducao', false);
            hideStopButton('traducao');
            // Re-habilitar botão principal
            var btnT = document.getElementById('btn-traduzir');
            if (btnT) btnT.disabled = false;

            if (error.name === 'AbortError') {
                activeRequest = null;
                activeModule = null;
                showError('traducao', 'Geração interrompida pelo usuário.');
            } else {
                showError('traducao',
                    'Não foi possível conectar ao servidor. Verifique se o backend está em execução (python app.py).'
                );
                console.error('Erro na tradução:', error);
            }
        }
    }

    // ========================================================================
    // PLANEJAMENTO PEDAGÓGICO (RF-011 a RF-013)
    // ========================================================================
    async function handlePlanning(e) {
        e.preventDefault();

        var tema = document.getElementById('tema').value.trim();
        var objetivos = document.getElementById('objetivos').value.trim();
        var perfil = document.getElementById('perfil').value;
        var perfilDetalhe = document.getElementById('perfil-detalhe').value.trim();
        var duracao = document.getElementById('duracao').value.trim();

        if (!tema || !objetivos || !perfil) {
            showAlert('Por favor, preencha todos os campos obrigatórios.', 'warning');
            return;
        }

        showLoading('planejamento', true);
        showStopButton('planejamento');   // Exibe o botão de parar independente
        hideResult('planejamento');

        try {
            if (activeRequest) activeRequest.abort();
            activeRequest = new AbortController();
            activeModule = 'planejamento';

            var useReasoningEl = document.getElementById('toggle-raciocinio');
            var useReasoning = useReasoningEl ? useReasoningEl.checked : false;

            var response = await fetch(API_BASE + '/api/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: activeRequest.signal,  // ← CORREÇÃO: conectar o sinal ao fetch
                body: JSON.stringify({
                    session_id: sessionId,
                    tema: tema,
                    objetivos: objetivos,
                    perfil: perfil,
                    perfil_detalhe: perfilDetalhe,
                    duracao: duracao || '50 minutos',
                    use_reasoning: useReasoning,
                    stream: true // ADICIONADO: Solicita o envio em tempo real ao backend
                })
            });

            if (!response.ok) throw new Error('Erro na requisição da rede');

            var reader = response.body.getReader();
            var decoder = new TextDecoder();
            var partialText = "";
            var isFirstChunk = true;

            var rawText = "";
            var isOllamaNativeThinking = false;
            var nativeThinkingText = "";

            showResult('planejamento');

            var contentEl = document.getElementById('result-planejamento-content');
            if (contentEl) {
                contentEl.innerHTML =
                    '<details id="reasoning-details-planejamento" style="margin-bottom: 15px; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; background-color: var(--bg-secondary);">' +
                    '<summary id="reasoning-summary-planejamento" style="cursor: pointer; font-weight: 600; color: var(--text-muted); list-style-position: inside;">🧠 Processo de raciocínio da IA<span class="jumping-dots"><span>.</span><span>.</span><span>.</span></span></summary>' +
                    '<div id="reasoning-content-planejamento" style="color: var(--text-muted); font-style: italic; font-size: 0.9em; margin-top: 10px; white-space: pre-wrap; font-family: monospace; max-height: 150px; overflow-y: auto;"></div>' +
                    '</details>' +
                    '<div id="final-content-planejamento"></div>';
            }

            while (true) {
                var { done, value } = await reader.read();
                if (done) break;

                // Remover tela de carregamento na primeira palavra
                if (isFirstChunk) {
                    showLoading('planejamento', false);
                    // Botão de parar já está visível (exibido antes do fetch)
                    isFirstChunk = false;
                }

                partialText += decoder.decode(value, { stream: true });
                var parts = partialText.split('\n\n');
                partialText = parts.pop() || '';

                for (var i = 0; i < parts.length; i++) {
                    var dataStr = parts[i].replace(/^data:\s*/, '').trim();
                    if (!dataStr) continue;

                    try {
                        var dataObj = JSON.parse(dataStr);

                        if (dataObj.done) {
                            hideStopButton('planejamento');
                            activeRequest = null;
                            activeModule = null;
                            showChatBox('planejamento');
                            var metaEl = document.getElementById('result-planejamento-meta');
                            if (metaEl) {
                                var selectPerfil = document.getElementById('perfil');
                                var nomePerfil = selectPerfil.options[selectPerfil.selectedIndex].text;
                                metaEl.innerHTML =
                                    '<span class="result-meta-item">🎯 Perfil: ' + nomePerfil + '</span>' +
                                    '<span class="result-meta-item">🔤 Tokens: ~' + (dataObj.tokens_used || 0) + '</span>' +
                                    '<span class="result-meta-item">⏱️ ' + (dataObj.response_time_ms || 0) + ' ms</span>';
                            }
                            break;
                        }

                        if (!dataObj.success) {
                            hideStopButton('planejamento');
                            showError('planejamento', dataObj.content || 'Erro ao gerar plano pedagógico.');
                            break;
                        }

                        var chunkText = dataObj.content || '';

                        if (dataObj.is_thinking) {
                            nativeThinkingText += chunkText;
                        } else {
                            rawText += chunkText;
                            var sum = document.getElementById('reasoning-summary-planejamento');
                            if (sum && !sum.dataset.done) {
                                sum.innerHTML = '🧠 Processo de raciocínio da IA';
                                sum.dataset.done = 'true';
                                var detailsBox = document.getElementById('reasoning-details-planejamento');
                                if (detailsBox) detailsBox.removeAttribute('open');
                            }
                        }

                        // Remove empty spaces at start
                        var displayFinal = rawText.replace(/^\s+/, '');

                        // Render
                        var rEl = document.getElementById('reasoning-content-planejamento');
                        if (rEl && nativeThinkingText.length > 0) {
                            rEl.textContent = nativeThinkingText;
                            rEl.scrollTop = rEl.scrollHeight; // Auto-scroll
                        }

                        var fEl = document.getElementById('final-content-planejamento');
                        if (fEl && displayFinal.length > 0) {
                            fEl.innerHTML = formatMarkdown(displayFinal);
                        }
                    } catch (err) { }
                }
            }
        } catch (error) {
            showLoading('planejamento', false);
            hideStopButton('planejamento');
            // Re-habilitar botão principal
            var btnP = document.getElementById('btn-planejar');
            if (btnP) btnP.disabled = false;

            if (error.name === 'AbortError') {
                activeRequest = null;
                activeModule = null;
                showError('planejamento', 'Geração interrompida pelo usuário.');
            } else {
                showError('planejamento', 'Não foi possível conectar ao servidor.');
            }
        }
    }

    // ========================================================================
    // CHAT DE REFINAMENTO
    // ========================================================================
    function showChatBox(tipo) {
        var chatEl = document.getElementById('chat-' + tipo);
        if (chatEl) {
            chatEl.style.display = 'block';
            // Limpar mensagens antigas de rodada anterior
            var msgs = document.getElementById('chat-messages-' + tipo);
            if (msgs) msgs.innerHTML = '';
        }
    }

    // Expor globalmente para onclick inline no HTML
    window.sendChatMessage = async function (tipo) {
        var inputEl = document.getElementById('chat-input-' + tipo);
        var btn = document.getElementById('chat-send-' + tipo);
        var msgsEl = document.getElementById('chat-messages-' + tipo);

        if (!inputEl || !msgsEl) return;
        var msg = inputEl.value.trim();
        if (!msg) return;

        // Adicionar mensagem do usuário
        appendChatMsg(msgsEl, msg, 'user');
        inputEl.value = '';
        btn.disabled = true;

        // Criar estrutura da mensagem da IA com IDs únicos para thinking e content
        var msgTimestamp = Date.now();
        var aiMsgDiv = document.createElement('div');
        aiMsgDiv.className = 'chat-msg chat-msg-ai';
        aiMsgDiv.id = 'chat-ai-msg-' + msgTimestamp;

        var detailsEl = document.createElement('details');
        detailsEl.className = 'thinking-details chat-thinking-details';
        detailsEl.id = 'chat-thinking-details-' + msgTimestamp;
        detailsEl.setAttribute('open', '');
        detailsEl.style.display = 'none';

        var summaryEl = document.createElement('summary');
        summaryEl.className = 'thinking-summary';
        summaryEl.innerHTML = '🧠 Processo de raciocínio da IA <span class="thinking-dots" id="chat-dots-' + msgTimestamp + '"><span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></span>';
        detailsEl.appendChild(summaryEl);

        var thinkingBoxEl = document.createElement('div');
        thinkingBoxEl.className = 'thinking-box';
        thinkingBoxEl.id = 'chat-thinking-box-' + msgTimestamp;
        detailsEl.appendChild(thinkingBoxEl);

        var contentDiv = document.createElement('div');
        contentDiv.className = 'chat-content-body';
        contentDiv.id = 'chat-content-' + msgTimestamp;

        var metaDiv = document.createElement('div');
        metaDiv.className = 'chat-msg-meta';
        metaDiv.id = 'chat-meta-' + msgTimestamp;
        metaDiv.style.display = 'none';

        aiMsgDiv.appendChild(detailsEl);
        aiMsgDiv.appendChild(contentDiv);
        aiMsgDiv.appendChild(metaDiv);
        msgsEl.appendChild(aiMsgDiv);
        msgsEl.scrollTop = msgsEl.scrollHeight;

        try {
            var res = await fetch(API_BASE + '/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    agent_type: tipo,
                    message: msg,
                    stream: true
                })
            });

            if (!res.ok) {
                contentDiv.innerHTML = '⚠️ Erro ao conectar ao servidor de chat.';
                return;
            }

            var reader = res.body.getReader();
            var decoder = new TextDecoder('utf-8');
            var partialLine = '';
            var fullResponseText = '';
            var hasStartedContent = false;

            while (true) {
                var { done, value } = await reader.read();
                if (done) break;

                partialLine += decoder.decode(value, { stream: true });
                var lines = partialLine.split('\n\n');
                partialLine = lines.pop(); // Mantém o chunk incompleto

                for (var line of lines) {
                    line = line.trim();
                    if (!line.startsWith('data: ')) continue;

                    var jsonStr = line.replace('data: ', '').trim();
                    try {
                        var dataObj = JSON.parse(jsonStr);

                        if (dataObj.done) {
                            var time = dataObj.response_time_ms ? dataObj.response_time_ms + ' ms' : '-';
                            var tokens = dataObj.tokens_used ? dataObj.tokens_used : '-';
                            metaDiv.innerHTML = `⏱️ ${time} &nbsp;|&nbsp; 🔤 ${tokens} tokens`;
                            metaDiv.style.display = 'block';

                            var dotsEl = document.getElementById('chat-dots-' + msgTimestamp);
                            if (dotsEl) dotsEl.style.display = 'none';
                            continue;
                        }

                        if (dataObj.is_thinking) {
                            if (detailsEl.style.display === 'none') {
                                detailsEl.style.display = 'block';
                            }
                            thinkingBoxEl.textContent += dataObj.content;
                            thinkingBoxEl.scrollTop = thinkingBoxEl.scrollHeight;
                        } else {
                            if (!hasStartedContent) {
                                hasStartedContent = true;
                                detailsEl.removeAttribute('open');
                                var dotsEl = document.getElementById('chat-dots-' + msgTimestamp);
                                if (dotsEl) dotsEl.style.display = 'none';
                            }
                            fullResponseText += dataObj.content;
                            contentDiv.innerHTML = formatMarkdown(fullResponseText);
                        }
                        msgsEl.scrollTop = msgsEl.scrollHeight;
                    } catch (e) {
                        console.error('Erro ao processar chunk SSE do chat:', e);
                    }
                }
            }
        } catch (err) {
            contentDiv.innerHTML = '⚠️ Não foi possível conectar ao servidor.';
        } finally {
            btn.disabled = false;
            msgsEl.scrollTop = msgsEl.scrollHeight;
        }
    };

    function appendChatMsg(container, text, role, metaData) {
        var div = document.createElement('div');
        div.className = 'chat-msg ' + (role === 'user' ? 'chat-msg-user' : 'chat-msg-ai');
        div.innerHTML = formatMarkdown(text);

        if (role === 'ai' && metaData) {
            var time = metaData.response_time_ms ? metaData.response_time_ms + ' ms' : '-';
            var tokens = metaData.tokens_used ? metaData.tokens_used : '-';

            var metaDiv = document.createElement('div');
            metaDiv.className = 'chat-msg-meta';
            metaDiv.innerHTML = `⏱️ ${time} &nbsp;|&nbsp; 🔤 ${tokens} tokens`;
            div.appendChild(metaDiv);
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    // ========================================================================
    // TELEMETRIA (RF-014, RF-015)
    // ========================================================================
    function initTelemetry() {
        var btnCSV = document.getElementById('btn-export-csv');
        if (btnCSV) {
            btnCSV.addEventListener('click', function () {
                exportTelemetry('csv');
            });
        }

        var btnTXT = document.getElementById('btn-export-txt');
        if (btnTXT) {
            btnTXT.addEventListener('click', function () {
                exportTelemetry('txt');
            });
        }

        var btnRefresh = document.getElementById('btn-refresh-telemetry');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', loadTelemetry);
        }
    }

    async function loadTelemetry() {
        try {
            var response = await fetch(API_BASE + '/api/telemetry');
            var data = await response.json();

            // Atualizar estatísticas
            var stats = data.estatisticas || {};
            setText('stat-total', stats.total_interacoes || 0);
            setText('stat-traducoes', stats.traducoes || 0);
            setText('stat-planejamentos', stats.planejamentos || 0);

            // Preencher tabela
            var tbody = document.getElementById('telemetry-tbody');
            if (!tbody) return;

            var historico = data.historico || [];

            if (historico.length === 0) {
                tbody.innerHTML =
                    '<tr><td colspan="5">' +
                    '<div class="empty-state">' +
                    '<div class="empty-state-icon">📊</div>' +
                    '<p class="empty-state-text">Nenhuma interação registrada</p>' +
                    '<p class="empty-state-hint">As interações aparecerão aqui após o uso dos agentes.</p>' +
                    '</div></td></tr>';
                return;
            }

            var rows = '';
            historico.forEach(function (record) {
                var ts = record.timestamp || '';
                var dateStr = ts ? new Date(ts).toLocaleString('pt-BR') : 'N/A';
                var agentType = record.agent_type || '';
                var badgeClass = agentType === 'traducao' ? 'badge-traducao' : 'badge-planejamento';
                var badgeText = agentType === 'traducao' ? 'Tradução' : 'Planejamento';
                var input = record.input || {};
                var inputText = input.termo || input.tema || JSON.stringify(input).substring(0, 50);
                var meta = record.metadata || {};
                var tokens = meta.tokens_used || '-';
                var time = meta.response_time_ms ? meta.response_time_ms + ' ms' : '-';

                rows +=
                    '<tr>' +
                    '<td>' + dateStr + '</td>' +
                    '<td><span class="badge ' + badgeClass + '">' + badgeText + '</span></td>' +
                    '<td title="' + escapeHtml(inputText) + '">' + escapeHtml(truncate(inputText, 40)) + '</td>' +
                    '<td>' + tokens + '</td>' +
                    '<td>' + time + '</td>' +
                    '</tr>';
            });

            tbody.innerHTML = rows;

        } catch (error) {
            console.error('Erro ao carregar telemetria:', error);
        }
    }

    function exportTelemetry(format) {
        window.open(API_BASE + '/api/telemetry/export?format=' + format, '_blank');
    }

    // ========================================================================
    // STATUS DO SISTEMA
    // ========================================================================
    async function checkSystemStatus() {
        try {
            var response = await fetch(API_BASE + '/api/status');
            var data = await response.json();

            // Status do LLM
            var llm = data.llm || {};
            updateStatusDot('llm-status-dot', llm.disponivel);

            var statusText = 'IA Offline';
            if (llm.disponivel) {
                if (llm.tipo === 'local') {
                    statusText = 'IA Online';
                } else {
                    statusText = 'IA Online (' + (llm.modelo || 'N/A') + ')';
                }
            }
            setText('llm-status-text', statusText);

            // Status do RAG
            var rag = data.rag || {};
            var ragDot = document.getElementById('rag-status-dot');
            if (ragDot) {
                ragDot.className = 'status-dot';
                if (rag.disponivel) {
                    ragDot.classList.add('online');
                } else if (rag.documentos === 0) {
                    ragDot.classList.add('warning');
                } else {
                    ragDot.classList.add('offline');
                }
            }
            setText('rag-status-text', rag.disponivel
                ? 'RAG: ' + (rag.trechos_indexados || 0) + ' trechos'
                : (rag.documentos === 0 ? 'RAG: Sem documentos' : 'RAG Offline')
            );

        } catch (error) {
            updateStatusDot('llm-status-dot', false);
            setText('llm-status-text', 'Servidor offline');
            updateStatusDot('rag-status-dot', false);
            setText('rag-status-text', 'Servidor offline');
        }
    }

    function updateStatusDot(id, online) {
        var dot = document.getElementById(id);
        if (dot) {
            dot.className = 'status-dot ' + (online ? 'online' : 'offline');
        }
    }

    // ========================================================================
    // UTILIDADES
    // ========================================================================

    function generateSessionId() {
        return 'sess_' + Math.random().toString(36).substring(2, 10);
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function showLoading(module, show) {
        var el = document.getElementById('loading-' + module);
        if (el) el.classList.toggle('visible', show);

        // Desabilitar botão durante loading
        var btnId = module === 'traducao' ? 'btn-traduzir' : 'btn-planejar';
        var btn = document.getElementById(btnId);
        if (btn) btn.disabled = show;
    }

    /**
     * Exibe o botão "Parar Geração" do módulo especificado.
     * O container é independente da div de loading para persistir durante o stream.
     */
    function showStopButton(module) {
        var container = document.getElementById('stop-btn-container-' + module);
        if (container) container.style.display = 'block';
    }

    /**
     * Oculta o botão "Parar Geração" do módulo especificado.
     */
    function hideStopButton(module) {
        var container = document.getElementById('stop-btn-container-' + module);
        if (container) container.style.display = 'none';
    }

    function showResult(module) {
        var el = document.getElementById('result-' + module);
        if (el) el.classList.add('visible');
    }

    function hideResult(module) {
        var el = document.getElementById('result-' + module);
        if (el) el.classList.remove('visible');
    }

    function showError(module, message) {
        var contentEl = document.getElementById('result-' + module + '-content');
        if (contentEl) {
            contentEl.innerHTML =
                '<div class="alert alert-error">' +
                '<span class="alert-icon">❌</span>' +
                '<span>' + escapeHtml(message) + '</span>' +
                '</div>';
        }
        showResult(module);
    }

    function showAlert(message, type) {
        // Alerta temporário no topo
        var alert = document.createElement('div');
        alert.className = 'alert alert-' + (type || 'info');
        alert.style.position = 'fixed';
        alert.style.top = '20px';
        alert.style.left = '50%';
        alert.style.transform = 'translateX(-50%)';
        alert.style.zIndex = '999';
        alert.style.maxWidth = '500px';
        alert.style.animation = 'fadeInDown 0.3s ease-out';
        alert.innerHTML =
            '<span class="alert-icon">' + (type === 'warning' ? '⚠️' : 'ℹ️') + '</span>' +
            '<span>' + escapeHtml(message) + '</span>';

        document.body.appendChild(alert);

        setTimeout(function () {
            alert.style.animation = 'fadeIn 0.3s ease-out reverse';
            setTimeout(function () {
                if (alert.parentNode) alert.parentNode.removeChild(alert);
            }, 300);
        }, 3000);
    }

    function costurarTabelasFragmentadas(markdownBruto) {
        var regexCostura = /(\|\s*\r?\n)\s*\r?\n(\s*\|)/g;
        var atual = markdownBruto;
        var anterior;
        do {
            anterior = atual;
            atual = atual.replace(regexCostura, '$1$2');
        } while (atual !== anterior);
        return atual;
    }

    function formatMarkdown(text) {
        if (!text) return '';

        var textoSaneado = costurarTabelasFragmentadas(escapeHtml(text));
        var rawLines = textoSaneado.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

        var lines = [];
        for (var i = 0; i < rawLines.length; i++) {
            var line = rawLines[i].trim();
            if (line === '') {
                var hasPrevPipe = (i > 0 && rawLines[i - 1].trim().startsWith('|'));
                var hasNextPipe = (i < rawLines.length - 1 && rawLines[i + 1].trim().startsWith('|'));
                if (hasPrevPipe && hasNextPipe) {
                    continue;
                }
            }
            lines.push(rawLines[i]);
        }

        var html = '';
        var inList = null; // 'ul', 'ol', ou null
        var inTable = false;
        var tableRows = [];

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();

            // 1. Detecção e Agrupamento de Tabelas
            if (line.startsWith('|')) {
                if (inList) {
                    html += '</' + inList + '>';
                    inList = null;
                }
                inTable = true;
                tableRows.push(line);
                continue;
            } else if (inTable) {
                html += renderTable(tableRows);
                tableRows = [];
                inTable = false;
            }

            // Ignorar linhas em branco (ou fechar tags abertas)
            if (line === '') {
                if (inList) {
                    html += '</' + inList + '>';
                    inList = null;
                }
                continue;
            }

            // 2. Títulos/Cabeçalhos (h1, h2, h3)
            var headerMatch = line.match(/^(#{1,3})\s+(.+)$/);
            if (headerMatch) {
                if (inList) {
                    html += '</' + inList + '>';
                    inList = null;
                }
                var level = headerMatch[1].length;
                html += '<h' + level + '>' + parseInline(headerMatch[2]) + '</h' + level + '>';
                continue;
            }

            // 3. Listas não ordenadas (Marcadores)
            var listMatch = line.match(/^[\s]*[•\-\*]\s+(.+)$/);
            if (listMatch) {
                if (inList !== 'ul') {
                    if (inList) html += '</' + inList + '>';
                    html += '<ul>';
                    inList = 'ul';
                }
                html += '<li>' + parseInline(listMatch[1]) + '</li>';
                continue;
            }

            // 4. Listas ordenadas
            var olMatch = line.match(/^[\s]*\d+\.\s+(.+)$/);
            if (olMatch) {
                if (inList !== 'ol') {
                    if (inList) html += '</' + inList + '>';
                    html += '<ol>';
                    inList = 'ol';
                }
                html += '<li>' + parseInline(olMatch[1]) + '</li>';
                continue;
            }

            // 5. Linhas divisorias (---)
            if (line === '---') {
                if (inList) {
                    html += '</' + inList + '>';
                    inList = null;
                }
                html += '<hr>';
                continue;
            }

            // 6. Parágrafo Padrão (linhas de texto comum)
            if (inList) {
                html += '</' + inList + '>';
                inList = null;
            }
            html += '<p>' + parseInline(lines[i]) + '</p>';
        }

        // Fechar tags abertas no final
        if (inTable) {
            html += renderTable(tableRows);
        }
        if (inList) {
            html += '</' + inList + '>';
        }

        return html;

        function parseInline(txt) {
            txt = txt.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            txt = txt.replace(/\*(.+?)\*/g, '<em>$1</em>');
            return txt;
        }

        function renderTable(rows) {
            var tableHtml = '<div class="table-container"><table class="data-table">';
            var headerDone = false;
            rows.forEach(function (r) {
                if (r.match(/^[\s\|\-\:]+$/)) return; // Ignora linha separadora como |---|

                var cells = r.split('|').map(function (c) { return c.trim(); }).filter(function (c, idx, arr) {
                    return idx > 0 && idx < arr.length - 1; // Ignora elementos das bordas vazias
                });
                if (cells.length === 0) return;

                tableHtml += '<tr>';
                cells.forEach(function (cell) {
                    if (!headerDone) {
                        tableHtml += '<th>' + parseInline(cell) + '</th>';
                    } else {
                        tableHtml += '<td>' + parseInline(cell) + '</td>';
                    }
                });
                tableHtml += '</tr>';
                headerDone = true;
            });
            tableHtml += '</table></div>';
            return tableHtml;
        }
    }


    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function truncate(text, maxLen) {
        if (!text) return '';
        return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && activeRequest && activeModule) {
            cancelGeneration(activeModule);
        }
    });

    /**
     * Cancela a geração ativa e reseta a interface do módulo correspondente
     * para permitir uma nova geração imediatamente, sem recarregar a página.
     *
     * @param {string} module - 'traducao' ou 'planejamento'
     */
    window.cancelGeneration = function (module) {
        if (activeRequest) {
            activeRequest.abort(); // Dispara AbortError no fetch
            activeRequest = null;
        }
        activeModule = null;

        // 1. Ocultar o spinner de loading
        showLoading(module, false);

        // 2. Ocultar o botão de parar
        hideStopButton(module);

        // 3. Re-habilitar o botão principal de envio
        var btnId = module === 'traducao' ? 'btn-traduzir' : 'btn-planejar';
        var btn = document.getElementById(btnId);
        if (btn) btn.disabled = false;

        // 4. Exibir alerta de cancelamento usando showError (exibe na área de resultado)
        showError(module, 'Geração interrompida pelo usuário.');
    };

})();
