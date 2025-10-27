# Parceiro de Programacao: Projeto Prisma - Fase 15 (Liderança Situacional)

import pygame
import sys
import re
import random
import json

pygame.init()

# --- Constantes e Configuração ---
LARGURA_TELA, ALTURA_TELA = 1280, 720
NOME_JOGO = "Projeto Prisma: Simulação de Liderança"
CORES = {"PRETO": (0,0,0), "BRANCO": (255,255,255), "AZUL": (100,149,237), "VERDE": (60,179,113), "VERMELHO": (205,92,92), "CINZA": (40,40,40), "CINZA_CLARO": (100,100,100), "AMARELO": (255,215,0), "ROXO": (148,0,211), 
         "AZUL_ESCURO": (65, 105, 225), # MUDANÇA: Cor adicionada
         "GRAFICO_RESPEITO": (255, 215, 0), "GRAFICO_DETERMINACAO": (102, 255, 102), "GRAFICO_ESTRESSE": (255, 102, 102), "GRAFICO_COMODIDADE": (102, 178, 255)}

try:
    FONTE_PIXEL = pygame.font.Font("assets/font/PressStart2P-Regular.ttf", 14)
    FONTE_PIXEL_PEQUENA = pygame.font.Font("assets/font/PressStart2P-Regular.ttf", 10)
    FONTE_TITULO = pygame.font.Font("assets/font/PressStart2P-Regular.ttf", 24)
    FONTES = {"TITULO": FONTE_TITULO, "TEXTO": FONTE_PIXEL, "BOTAO": FONTE_PIXEL_PEQUENA, "DIALOGO": FONTE_PIXEL}
except FileNotFoundError:
    print("Aviso: Fonte pixel não encontrada. Usando Arial.")
    FONTES = {"TITULO": pygame.font.SysFont('Arial', 32), "TEXTO": pygame.font.SysFont('Arial', 24), "BOTAO": pygame.font.SysFont('Arial', 18), "DIALOGO": pygame.font.SysFont('Arial', 28)}

tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption(NOME_JOGO)

# =========================================================================
# 2. MOTOR DO JOGO: CLASSES E ESTRUTURAS
# =========================================================================

class Projeto:
    def __init__(self):
        self.pontos_de_projeto = 0; self.dia_atual = 1; self.meta_pontos = 250
        self.dias_da_semana = {1: "Segunda-feira", 2: "Terça-feira", 3: "Quarta-feira", 4: "Quinta-feira", 5: "Sexta-feira"}
    def get_dia_semana(self): return self.dias_da_semana.get(self.dia_atual, "")

class Funcionario:
    def __init__(self, nome, geracao, status_base):
        self.nome, self.geracao = nome, geracao
        self.respeito, self.determinacao, self.estresse, self.comodidade = status_base['respeito'], status_base['determinacao'], status_base['estresse'], status_base['comodidade']
        self.limiar_estresse = 5
        if self.nome == "Carlos": self.limiar_estresse = 6
        elif self.nome == "Júlia": self.limiar_estresse = 4
        self.historico_status = []
    def guardar_status_do_dia(self, dia):
        self.historico_status.append({"dia": dia, "respeito": self.respeito, "determinacao": self.determinacao, "estresse": self.estresse, "comodidade": self.comodidade})

class Lider:
    def __init__(self, nome, dados):
        self.nome = nome
        self.descricao = dados.get('descricao', '')
        self.pontos_acao = 3; self.max_pontos_acao = 3
        self.habilidade_nome = dados.get('habilidade_nome', 'Nenhuma')
        self.habilidade_custo = dados.get('habilidade_custo', 0)
        self.habilidade_requer_alvo = dados.get('habilidade_requer_alvo', False)
        # UPDATE: Changed counters to reflect Situational Leadership styles
        self.contadores = {
            "determinar_eficaz": 0, "determinar_ineficaz": 0,
            "orientar_eficaz": 0, "orientar_ineficaz": 0,
            "apoiar_eficaz": 0, "apoiar_ineficaz": 0,
            "delegar_eficaz": 0, "delegar_ineficaz": 0
        }
    def aplicar_passiva(self, equipe): pass
    def usar_habilidade_ativa(self, game_manager, alvo=None): return False

class DiretorAutocrata(Lider):
    def aplicar_passiva(self, equipe):
        for f in equipe:
            if f.geracao == "Baby Boomer": f.respeito += 2
            elif f.geracao == "Geração Z": f.respeito -= 2
    def usar_habilidade_ativa(self, game_manager, alvo):
        if alvo:
            # Note: Hability usage doesn't directly map to situational style counters
            game_manager.modificar_status(alvo, "estresse", 2); game_manager.modificar_status(alvo, "pontos_de_projeto", 20); return True
        return False

class VisionarioTransformacional(Lider):
    def aplicar_passiva(self, equipe):
        for f in equipe:
            if f.geracao == "Millennial": f.respeito += 2
    def usar_habilidade_ativa(self, game_manager, alvo=None):
        for f in game_manager.equipe: game_manager.modificar_status(f, "determinacao", 2)
        return True

class LiderServidor(Lider):
    def usar_habilidade_ativa(self, game_manager, alvo):
        if alvo: game_manager.modificar_status(alvo, "estresse", -3); return True
        return False

class OpcaoDialogo:
    def __init__(self, texto, efeitos, tipo, eficacia):
        self.texto_resposta = texto
        self.efeitos = efeitos
        self.tipo = tipo # Now expects "determinar", "orientar", "apoiar", "delegar"
        self.eficacia = eficacia # Still "eficaz" or "ineficaz"

class NoDialogo:
    def __init__(self, frase, lista_de_opcoes):
        self.frase_abertura = frase
        self.opcoes = lista_de_opcoes

class Evento:
    def __init__(self, titulo, desc, op1_txt, op1_ef, op2_txt, op2_ef, id_evento=""):
        self.titulo, self.descricao = titulo, desc
        self.id_evento = id_evento # Store the event ID
        # Event options might have direct effects now
        self.opcoes = [OpcaoDialogo(op1_txt, op1_ef, "evento", "neutro"),
                       OpcaoDialogo(op2_txt, op2_ef, "evento", "neutro")]


def parse_efeitos(texto):
    if not texto: return []
    mapa = {"Respeito": "respeito", "Comodidade": "comodidade", "Projeto": "pontos_de_projeto", "Estresse": "estresse", "Determinação": "determinacao"}
    efeitos = []
    # Permitir comentários no final da linha
    texto_sem_comentario = texto.split('//')[0].strip()
    matches = re.findall(r"(\w+)\s*([+-])(\d+)", texto_sem_comentario)
    for nome, sinal, valor_str in matches:
        if (atributo := mapa.get(nome)):
            valor = int(valor_str) * (-1 if sinal == '-' else 1)
            efeitos.append({"atributo": atributo, "valor": valor})
    return efeitos

# --- NOVA FUNÇÃO ---
# Esta função calcula a altura total que um texto multi-linha ocupará
def calcular_altura_texto(text, rect_width, font):
    linhas = []
    palavras = text.split(' ')
    linha_atual = ''
    for palavra in palavras:
        linha_teste = f"{linha_atual} {palavra}".strip()
        if font.size(linha_teste)[0] > rect_width:
            linhas.append(linha_atual)
            linha_atual = palavra
        else:
            linha_atual = linha_teste
    linhas.append(linha_atual)
    
    # Conta apenas linhas não vazias
    linhas_validas = [l for l in linhas if l.strip()]
    # Retorna a altura total (num linhas * altura da fonte)
    return len(linhas_validas) * font.get_linesize()
# --- FIM DA NOVA FUNÇÃO ---

def desenhar_texto_multilinha(surface, text, rect, font, color, centralizado=False): # MUDANÇA: Adicionado 'centralizado'
    linhas = []; palavras = text.split(' '); linha_atual = ''
    for palavra in palavras:
        linha_teste = f"{linha_atual} {palavra}".strip()
        if font.size(linha_teste)[0] > rect.width:
            linhas.append(linha_atual); linha_atual = palavra
        else: linha_atual = linha_teste
    linhas.append(linha_atual)
    y = rect.top + 5
    for linha in linhas:
        if linha.strip():
            img = font.render(linha, True, color)
            
            # --- LÓGICA DE CENTRALIZAÇÃO ---
            pos_x = rect.left + 5 # Padrão (esquerda)
            if centralizado:
                pos_x = rect.centerx - (img.get_width() // 2)
            # --- FIM DA LÓGICA ---

            surface.blit(img, (pos_x, y)); y += font.get_linesize()

def desenhar_barra_status(surface, rect, valor_atual, valor_max, cor_cheia, cor_vazia=CORES["CINZA"]):
    # Garante que o valor não passe do limite
    valor_atual = max(0, min(valor_atual, valor_max))
    
    # 1. Desenha o fundo (a barra vazia)
    pygame.draw.rect(surface, cor_vazia, rect, border_radius=3)
    
    if valor_atual > 0:
        # 2. Calcula a largura da barra cheia
        largura_cheia = (valor_atual / valor_max) * rect.width
        rect_cheia = pygame.Rect(rect.left, rect.top, int(largura_cheia), rect.height)
        
        # 3. Desenha a barra cheia por cima
        pygame.draw.rect(surface, cor_cheia, rect_cheia, border_radius=3)

class Botao:
    def __init__(self, x, y, l, a, t="", cor=CORES["BRANCO"], ativo=True): # MUDANÇA: Cor padrão para BRANCO
        self.rect = pygame.Rect(x, y, l, a); self.texto, self.cor_fundo, self.ativo = t, cor, ativo
    
    def desenhar(self, surface, pos_mouse_hover=(0,0), imagem_ativa=None, imagem_inativa=None):
        imagem_para_desenhar = None
        if self.ativo and imagem_ativa:
            imagem_para_desenhar = imagem_ativa
        elif not self.ativo and imagem_inativa:
            imagem_para_desenhar = imagem_inativa
        
        if imagem_para_desenhar:
            surface.blit(imagem_para_desenhar, self.rect.topleft)
        else:
            # Lógica de Hover: Muda a cor se o mouse estiver sobre o botão
            cor = self.cor_fundo
            if not self.ativo:
                cor = CORES["CINZA"]
            elif self.rect.collidepoint(pos_mouse_hover):
                cor = CORES["CINZA_CLARO"] # MUDANÇA: Cor de Hover para CINZA_CLARO
            
            pygame.draw.rect(surface, cor, self.rect, border_radius=5)

        if self.texto:
            cor_texto = CORES["PRETO"] # MUDANÇA: Cor do texto para PRETO
            fonte = FONTES["TEXTO"] if self.rect.height >= 70 else FONTES["BOTAO"]
            # Render multi-line text if needed for dialogue options
            if '\n' in self.texto or fonte.size(self.texto)[0] > self.rect.width - 10:
                 desenhar_texto_multilinha(surface, self.texto, self.rect.inflate(-10, -10), fonte, cor_texto)
            else:
                 texto_surf = fonte.render(self.texto, True, cor_texto)
                 texto_rect = texto_surf.get_rect(center=self.rect.center)
                 surface.blit(texto_surf, texto_rect)


    def foi_clicado(self, pos): return self.ativo and self.rect.collidepoint(pos)

# =========================================================================
# 3. CONTEÚDO DO JOGO (Carregado de ficheiros externos)
# =========================================================================

def carregar_banco_dialogos_de_json(nome_ficheiro):
    banco = {}
    try:
        # User confirmed file naming convention
        with open(f"gamedata/{nome_ficheiro}", 'r', encoding='utf-8') as f:
            dados = json.load(f)
            for item in dados:
                dia, gatilho = item['dia'], item['gatilho']
                lista_opcoes = []
                for opt in item.get('opcoes', []):
                    efeitos = parse_efeitos(opt.get('efeito', ''))
                    # UPDATE: Expecting situational leadership types now
                    tipo = opt.get('tipo', 'apoiar') # Default to 'apoiar' if missing
                    eficacia = opt.get('eficacia', 'ineficaz') # Default to 'ineficaz'
                    lista_opcoes.append(OpcaoDialogo(opt.get('texto', ''), efeitos, tipo, eficacia))
                banco.setdefault(dia, {})[gatilho] = NoDialogo(item['frase'], lista_opcoes)
    except FileNotFoundError: print(f"AVISO: Ficheiro 'gamedata/{nome_ficheiro}' não encontrado."); return {}
    except Exception as e: print(f"ERRO ao carregar '{nome_ficheiro}': {e}"); return {}
    return banco

def carregar_dados_json(nome_ficheiro):
    try:
        # User confirmed file naming convention
        with open(f"gamedata/{nome_ficheiro}", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError: print(f"AVISO: Ficheiro 'gamedata/{nome_ficheiro}' não encontrado.")
    except Exception as e: print(f"ERRO ao carregar '{nome_ficheiro}': {e}")
    return None

# =========================================================================
# 4. GERENCIADOR PRINCIPAL DO JOGO (O "CÉREBRO")
# =========================================================================

class GameManager:
    def __init__(self):
        self.estado_jogo = "TELA_DE_ESCOLHA"; self.projeto = Projeto()
        
        self.imagens = self.carregar_todas_imagens()

        dados_equipe = carregar_dados_json("equipe.json") or []
        status_base = {"respeito": 5, "determinacao": 7, "estresse": 3, "comodidade": 2}
        self.equipe = [Funcionario(d['nome'], d['geracao'], status_base) for d in dados_equipe]
        
        dados_lideres = carregar_dados_json("lideres.json") or {}
        self.arquetipos_disponiveis = []
        for nome, dados in dados_lideres.items():
            if nome == "Diretor Autocrata": self.arquetipos_disponiveis.append(DiretorAutocrata(nome, dados))
            elif nome == "Visionário Transformacional": self.arquetipos_disponiveis.append(VisionarioTransformacional(nome, dados))
            elif nome == "Líder Servidor": self.arquetipos_disponiveis.append(LiderServidor(nome, dados))

        # User confirmed file naming convention for dialogues
        self.banco_dialogos = {f.nome: carregar_banco_dialogos_de_json(f"{f.nome.lower().replace('ú', 'u')}.json") for f in self.equipe}
        # User confirmed file naming convention for events and structure from eventos_reestruturado.json
        self.banco_eventos = [Evento(e['titulo'], e['desc'], e['op1_txt'], parse_efeitos(e['op1_ef']), e['op2_txt'], parse_efeitos(e['op2_ef']), e.get('id_evento', '')) for e in (carregar_dados_json("eventos.json") or [])]
        self.banco_feedbacks = carregar_dados_json("feedbacks.json") or {}

        self.lider_escolhido = None
        self.botoes_escolha_lider = [Botao(LARGURA_TELA/2-175, 150+i*100, 350, 70, a.nome) for i, a in enumerate(self.arquetipos_disponiveis)]
        self.botao_finalizar_dia = Botao(LARGURA_TELA-250, ALTURA_TELA-70, 200, 50, "Finalizar Dia")
        self.botao_sair = Botao(LARGURA_TELA - 120, 15, 100, 40, "Sair", CORES["VERMELHO"]) # Y=15
        self.evento_atual = None; self.botoes_evento = []
        self.no_dialogo_atual = None; self.botoes_dialogo = []; self.funcionario_em_dialogo = None
        
        # MUDANÇA: Cards movidos para Y=100 e altura diminuída para 480
        self.card_rects = [pygame.Rect(40 + i * 310, 100, 280, 480) for i in range(len(self.equipe))]
        # Botões de conversar agora calculam o 'bottom' com base na nova altura (sem sobreposição)
        self.botoes_conversar = {f.nome: Botao(self.card_rects[i].centerx - 90, self.card_rects[i].bottom + 5, 180, 50, "Conversar") for i, f in enumerate(self.equipe)} # Y +5

        self.funcionarios_conversados_hoje = []
        self.botao_habilidade = None; self.feedback_texto = ""; self.feedback_timer = 0
        self.resultado_final = ""; self.feedback_final_gerado = None
        
        # Store the current day's event ID
        self.id_evento_do_dia = None
        # --- SURFACES SEMI-TRANSPARENTES (para o HUD) ---
        self.hud_top_surface = pygame.Surface((LARGURA_TELA, 70), pygame.SRCALPHA)
        self.hud_top_surface.fill((0, 0, 0, 120)) # Fundo preto, 120/255 de opacidade (Mais transparente)
        
        self.hud_bottom_surface = pygame.Surface((LARGURA_TELA, 80), pygame.SRCALPHA)
        self.hud_bottom_surface.fill((0, 0, 0, 80)) # (Mais transparente)
        
    def carregar_todas_imagens(self):
        imagens = {}
        nomes = ["bruno", "julia", "carlos", "sandra"]
        humores = ["neutro", "determinado", "estressado", "acomodado"]
        
        try:
            # Fundos e UI
            imagens['fundo_fabrica'] = pygame.transform.scale(pygame.image.load("assets/fundo_fabrica.png").convert(), (LARGURA_TELA, ALTURA_TELA))
            
            # REMOVIDO: Carregamento de imagens de UI (caixa_dialogo, botoes)
            
            # Carregar retratos redimensionados
            TAMANHO_RETRATO = (240, 220) # Define o tamanho padrão aqui
            for nome_arquivo in nomes:
                for humor in humores:
                    # User confirmed file naming convention for cards
                    caminho = f"assets/{nome_arquivo}_retrato_{humor}.png"
                    try:
                        img = pygame.image.load(caminho).convert_alpha()
                        # Redimensiona NO CARREGAMENTO e armazena na RAIZ do dict
                        imagens[f"{nome_arquivo}_retrato_{humor}"] = pygame.transform.scale(img, TAMANHO_RETRATO)
                    except pygame.error:
                        print(f"AVISO: Retrato não encontrado: {caminho}")
                        imagens[f"{nome_arquivo}_retrato_{humor}"] = None # Adiciona None se falhar

            # Fundos de relatório
            imagens['fundo_sucesso'] = pygame.transform.scale(pygame.image.load("assets/fundo_sucesso.png").convert(), (LARGURA_TELA, ALTURA_TELA))
            imagens['fundo_fracasso'] = pygame.transform.scale(pygame.image.load("assets/fundo_fracasso.png").convert(), (LARGURA_TELA, ALTURA_TELA))

        except pygame.error as e:
            print(f"Erro ao carregar imagem: {e}. Verifique a pasta 'assets' e os nomes dos arquivos.")
        return imagens
        self.botao_sair.desenhar(surface, pos_mouse_hover)
        # --- FIM DO NOVO LAYOUT ---

    def processar_input(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        pos_mouse = event.pos
        if self.botao_sair.foi_clicado(pos_mouse): pygame.quit(); sys.exit()

        if self.estado_jogo == "TELA_DE_ESCOLHA":
            for i, botao in enumerate(self.botoes_escolha_lider):
                if botao.foi_clicado(pos_mouse):
                    self.lider_escolhido = self.arquetipos_disponiveis[i]
                    self.lider_escolhido.aplicar_passiva(self.equipe)
                    self.botao_habilidade = Botao(LARGURA_TELA/2 - 110, ALTURA_TELA-70, 220, 50, f"{self.lider_escolhido.habilidade_nome} ({self.lider_escolhido.habilidade_custo} PA)")
                    # Start the first day right after choosing leader
                    self.avancar_dia(primeiro_dia=True)
        elif self.estado_jogo == "JOGO_PRINCIPAL":
            for nome, botao in self.botoes_conversar.items():
                if botao.foi_clicado(pos_mouse): self.iniciar_dialogo(nome)
            if self.botao_finalizar_dia.foi_clicado(pos_mouse): self.avancar_dia()
        elif self.estado_jogo == "TELA_DIALOGO":
            for i, botao in enumerate(self.botoes_dialogo):
                if botao.foi_clicado(pos_mouse):
                    opcao = self.no_dialogo_atual.opcoes[i]
                    # UPDATE: Increment situational leadership counters
                    contador_key = f"{opcao.tipo}_{opcao.eficacia}"
                    if contador_key in self.lider_escolhido.contadores:
                        self.lider_escolhido.contadores[contador_key] += 1
                    else:
                        # Fallback for old/mistyped types, count as 'apoiar_ineficaz'
                        print(f"AVISO: Contador não encontrado para {contador_key}. Verifique o JSON. Contando como 'apoiar_ineficaz'.")
                        self.lider_escolhido.contadores["apoiar_ineficaz"] += 1

                    self.aplicar_efeitos(opcao.efeitos, self.funcionario_em_dialogo)
                    self.estado_jogo = "JOGO_PRINCIPAL" # Return to main game screen
        elif self.estado_jogo == "TELA_EVENTO":
             for i, botao in enumerate(self.botoes_evento):
                if botao.foi_clicado(pos_mouse):
                    # Apply the event's direct effects chosen by the player
                    self.aplicar_efeitos(self.evento_atual.opcoes[i].efeitos, source='event') # Pass source='event'
                    self.estado_jogo = "JOGO_PRINCIPAL" # Go to main game screen after choosing event option


    def get_humor_funcionario(self, funcionario):
        status_humor = {
            "determinado": funcionario.determinacao,
            "estressado": funcionario.estresse,
            "acomodado": funcionario.comodidade
        }
        valor_max = max(status_humor.values())
        humores_max = [humor for humor, valor in status_humor.items() if valor == valor_max]
        if len(humores_max) == 1:
            return humores_max[0]
        return "neutro"

    def iniciar_dialogo(self, nome_funcionario):
        if not self.lider_escolhido or self.lider_escolhido.pontos_acao < 1: self.mostrar_feedback("Pontos de Ação insuficientes!"); return
        if nome_funcionario in self.funcionarios_conversados_hoje: self.mostrar_feedback(f"Já conversou com {nome_funcionario} hoje."); return
        self.lider_escolhido.pontos_acao -= 1; self.funcionarios_conversados_hoje.append(nome_funcionario)
        self.funcionario_em_dialogo = next((f for f in self.equipe if f.nome == nome_funcionario), None)
        if not self.funcionario_em_dialogo: return
        dia = self.projeto.get_dia_semana()
        
        # Now, dialogues might depend on the event of the day AND mood
        # For simplicity, we stick to the mood-based trigger as requested
        # We assume the dialogue text itself implicitly reflects the event context
        dialogos_do_dia = self.banco_dialogos.get(nome_funcionario, {}).get(dia)
        
        if not dialogos_do_dia:
            print(f"AVISO: Nenhum diálogo para {nome_funcionario} na {dia}."); self.funcionarios_conversados_hoje.pop(); self.lider_escolhido.pontos_acao += 1; return
        
        f = self.funcionario_em_dialogo
        humor_map = {"determinado": "Determinacao Alta", "estressado": "Estresse Alto", "acomodado": "Comodismo Alto"}
        humor_atual = self.get_humor_funcionario(f)
        
        gatilho_humor = humor_map.get(humor_atual, "Padrão")
        # Try mood trigger first, then default 'Padrão'
        gatilhos_prioritarios = [gatilho_humor, "Padrão"]
        
        for gatilho in gatilhos_prioritarios:
            if gatilho in dialogos_do_dia:
                self.no_dialogo_atual = dialogos_do_dia[gatilho]
                self.criar_botoes_dialogo()
                self.estado_jogo = "TELA_DIALOGO"
                return
        
        # Fallback if even 'Padrão' isn't found for the day
        print(f"AVISO: Gatilho '{gatilho_humor}' ou 'Padrão' não encontrado para {nome_funcionario} na {dia}.")
        self.funcionarios_conversados_hoje.pop(); self.lider_escolhido.pontos_acao += 1


    def criar_botoes_dialogo(self):
        self.botoes_dialogo = []
        opcoes = self.no_dialogo_atual.opcoes
        
        # --- LÓGICA ATUALIZADA PARA GRID 2x2 ---
        # 1. Definir a área do grid (terço inferior)
        altura_grid = ALTURA_TELA // 3 # 720 / 3 = 240
        pos_y_grid_inicio = ALTURA_TELA - altura_grid - 20 # Começa em y=460
        
        # 2. Definir colunas e larguras
        margem_lateral = 40
        margem_central = 20
        largura_botao = (LARGURA_TELA - (margem_lateral * 2) - margem_central) // 2
        altura_botao = (altura_grid - 40) // 2 # Duas linhas com 20px de margem
        
        pos_x_col1 = margem_lateral
        pos_x_col2 = margem_lateral + largura_botao + margem_central
        
        pos_y_row1 = pos_y_grid_inicio
        pos_y_row2 = pos_y_grid_inicio + altura_botao + 20

        posicoes = [
            (pos_x_col1, pos_y_row1), # Botão 0
            (pos_x_col2, pos_y_row1), # Botão 1
            (pos_x_col1, pos_y_row2), # Botão 2
            (pos_x_col2, pos_y_row2)  # Botão 3
        ]
        # --- FIM DA LÓGICA ATUALIZADA ---

        for i, o in enumerate(opcoes):
            if i < len(posicoes): # Garante que não temos mais de 4 opções
                pos_x, pos_y = posicoes[i]
                self.botoes_dialogo.append(Botao(pos_x, pos_y, largura_botao, altura_botao, o.texto_resposta))

    # --- NOVA FUNÇÃO ---
    def criar_botoes_evento(self):
        self.botoes_evento = []
        opcoes = self.evento_atual.opcoes
        
        # Lógica do grid 2x2 (copiada de criar_botoes_dialogo)
        altura_grid = ALTURA_TELA // 3 # 240
        pos_y_grid_inicio = ALTURA_TELA - altura_grid - 20 # y=460
        
        margem_lateral = 40
        margem_central = 20
        largura_botao = (LARGURA_TELA - (margem_lateral * 2) - margem_central) // 2
        altura_botao = (altura_grid - 40) // 2 
        
        pos_x_col1 = margem_lateral
        pos_x_col2 = margem_lateral + largura_botao + margem_central
        
        pos_y_row1 = pos_y_grid_inicio
        pos_y_row2 = pos_y_grid_inicio + altura_botao + 20

        # Eventos só têm 2 opções, então usamos as duas posições de cima
        posicoes = [
            (pos_x_col1, pos_y_row1), # Botão 0
            (pos_x_col2, pos_y_row1), # Botão 1
        ]

        for i, o in enumerate(opcoes):
            if i < len(posicoes): 
                pos_x, pos_y = posicoes[i]
                # Faz os botões de evento ocuparem a largura toda se forem só 2
                # (Ajuste opcional, mas fica bom)
                largura_final = largura_botao
                if len(opcoes) == 2:
                    largura_final = LARGURA_TELA - (margem_lateral * 2) # Ocupa a linha toda
                    pos_x = margem_lateral
                    if i == 1: # Se for o segundo botão
                        pos_y = pos_y_row2 # Joga para a segunda linha
                
                self.botoes_evento.append(Botao(pos_x, pos_y, largura_final, altura_botao, o.texto_resposta))
    # --- FIM DA NOVA FUNÇÃO ---            



    def aplicar_efeitos(self, efeitos, alvo_especifico=None, source='dialog'): # Added source
        alvos = [alvo_especifico] if alvo_especifico else self.equipe
        for efeito in efeitos:
            # Check if effect comes from an event option (affects everyone) or dialogue (specific target)
            current_alvos = self.equipe if source == 'event' else alvos
            for alvo in current_alvos:
                 if alvo: self.modificar_status(alvo, efeito['atributo'], efeito['valor'])


    def modificar_status(self, funcionario, atributo, valor):
        if atributo == "pontos_de_projeto":
            self.projeto.pontos_de_projeto += valor
        else:
            setattr(funcionario, atributo, max(0, min(10, getattr(funcionario, atributo) + valor)))

    def mostrar_feedback(self, texto, duracao=120): self.feedback_texto = texto; self.feedback_timer = duracao
    
    def desenhar(self, surface):
        pos_mouse_hover = pygame.mouse.get_pos()
        mapa = {"TELA_DE_ESCOLHA": self.desenhar_tela_escolha, "TELA_EVENTO": self.desenhar_tela_evento, "TELA_DIALOGO": self.desenhar_tela_dialogo, "MODO_ALVO": self.desenhar_hud_jogo, "TELA_RELATORIO_FINAL": self.desenhar_tela_relatorio}
        desenho_func = mapa.get(self.estado_jogo, self.desenhar_hud_jogo)
        desenho_func(surface, pos_mouse_hover)
        
    def desenhar_tela_dialogo(self, surface, pos_mouse_hover=(0,0)):
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        # --- LAYOUT DE DIÁLOGO COMPLETAMENTE NOVO ---

        # 1. Definir e desenhar a caixa de diálogo principal (larga)
        # (Posicionada acima do grid de botões)
        altura_caixa = 250
        caixa_dialogo_rect = pygame.Rect(40, (ALTURA_TELA // 2) - (altura_caixa // 2) - 50, LARGURA_TELA - 80, altura_caixa)
        pygame.draw.rect(surface, CORES["CINZA"], caixa_dialogo_rect, border_radius=10)

        # 2. Carregar e desenhar o retrato do funcionário (à direita)
        retrato_img = None
        TAMANHO_RETRATO = (240, 220) # Mesmo tamanho do card
        if self.funcionario_em_dialogo:
            nome_arquivo = self.funcionario_em_dialogo.nome.lower().replace('ú', 'u')
            humor = self.get_humor_funcionario(self.funcionario_em_dialogo)
            retrato_img_key = f"{nome_arquivo}_retrato_{humor}"
            
            # --- DEBUG ADICIONADO ---
            # print(f"[DEBUG] Procurando retrato com a chave: '{retrato_img_key}'")
            # --- FIM DO DEBUG ---
            
            retrato_img = self.imagens.get(retrato_img_key)

        if retrato_img:
            # Redimensiona se necessário (o código de carregar já faz, mas é uma garantia)
            if retrato_img.get_size() != TAMANHO_RETRATO:
                 retrato_img = pygame.transform.scale(retrato_img, TAMANHO_RETRATO)
            
            # Posiciona o retrato dentro da caixa, à direita
            pos_retrato_x = caixa_dialogo_rect.right - TAMANHO_RETRATO[0] - 15
            pos_retrato_y = caixa_dialogo_rect.centery - (TAMANHO_RETRATO[1] // 2)
            surface.blit(retrato_img, (pos_retrato_x, pos_retrato_y))
        else:
            # --- DEBUG ADICIONADO ---
            if self.funcionario_em_dialogo: # Só imprime se deveria haver um funcionário
                print(f"[DEBUG] FALHA: Retrato não encontrado no dict self.imagens. Chave '{retrato_img_key}' retornou None.")
            # --- FIM DO DEBUG ---
        
        largura_retrato_com_margem = TAMANHO_RETRATO[0] + 30 if retrato_img else 0

        # 3. Desenhar o Título (Nome do funcionário) - (À esquerda)
        titulo_surf = FONTES["TITULO"].render(f"{self.funcionario_em_dialogo.nome} diz:", True, CORES["BRANCO"])
        titulo_rect = titulo_surf.get_rect(left=caixa_dialogo_rect.left + 30, top=caixa_dialogo_rect.top + 25)
        surface.blit(titulo_surf, titulo_rect)

        # 4. Desenhar o Texto da Fala (À esquerda, com quebra de linha)
        # O retângulo do texto agora é menor para não sobrepor o retrato
        largura_texto = caixa_dialogo_rect.width - largura_retrato_com_margem - 60 # 30 margem esq, 30 margem dir
        rect_texto = pygame.Rect(caixa_dialogo_rect.left + 30, caixa_dialogo_rect.top + 80, largura_texto, caixa_dialogo_rect.height - 100)
        desenhar_texto_multilinha(surface, f'"{self.no_dialogo_atual.frase_abertura}"', rect_texto, FONTES["DIALOGO"], CORES["BRANCO"])
        
        # 5. Desenhar os botões do grid (já calculados)
        for b in self.botoes_dialogo: 
            b.desenhar(surface, pos_mouse_hover)
        
        self.botao_sair.desenhar(surface, pos_mouse_hover)
        # --- FIM DO NOVO LAYOUT ---


    def desenhar_hud_jogo(self, surface, pos_mouse_hover=(0,0)):
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        # --- 1. HUD Superior (Barra de Infos) ---
        surface.blit(self.hud_top_surface, (0, 0))
        
        # Dia (Destaque)
        dia_surf = FONTES["TITULO"].render(f"{self.projeto.get_dia_semana()}", True, CORES["BRANCO"])
        dia_rect = dia_surf.get_rect(left=30, centery=35)
        surface.blit(dia_surf, dia_rect)

        if self.lider_escolhido:
            # PA (Evidente) - MUDANÇA: Cor trocada para AZUL_ESCURO
            pa_surf = FONTES["TITULO"].render(f"PA: {self.lider_escolhido.pontos_acao}", True, CORES["AZUL_ESCURO"])
            pa_rect = pa_surf.get_rect(centerx=LARGURA_TELA/2, centery=35)
            surface.blit(pa_surf, pa_rect)
        
        # Pontos (Corrigido e alinhado à direita)
        # MUDANÇA: Texto completo e fonte menor para caber
        pontos_str = f"Pontos de Projeto: {self.projeto.pontos_de_projeto}/{self.projeto.meta_pontos}"
        pontos_surf = FONTES["TEXTO"].render(pontos_str, True, CORES["BRANCO"]) # Fonte TEXTO (14px)
        pontos_rect = pontos_surf.get_rect(right=LARGURA_TELA - 140, centery=35) # 140px de margem (botão sair)
        surface.blit(pontos_surf, pontos_rect)
        
        # Botão Sair (Dentro do HUD)
        self.botao_sair.desenhar(surface, pos_mouse_hover) # Posição já foi atualizada no __init__
        
        
        # --- 2. Cards dos Funcionários (Layout Interno Corrigido) ---
        for i, f in enumerate(self.equipe):
            card_rect = self.card_rects[i]
            
            # 1. Fundo do card
            pygame.draw.rect(surface, CORES["CINZA"], card_rect, border_radius=10)

            # 2. Retrato
            retrato_img = None
            TAMANHO_RETRATO = (240, 220) 
            
            nome_arquivo = f.nome.lower().replace('ú', 'u')
            humor = self.get_humor_funcionario(f)
            retrato_img_key = f"{nome_arquivo}_retrato_{humor}"
            retrato_img = self.imagens.get(retrato_img_key)

            # Posição Y do retrato (relativa ao card)
            pos_retrato_y = card_rect.top + 15

            if retrato_img:
                if retrato_img.get_size() != TAMANHO_RETRATO:
                    retrato_img = pygame.transform.scale(retrato_img, TAMANHO_RETRATO)
                
                pos_retrato_x = card_rect.centerx - (TAMANHO_RETRATO[0] // 2)
                surface.blit(retrato_img, (pos_retrato_x, pos_retrato_y))
            
            # 3. Nome do Funcionário (Posição Y Corrigida)
            # Y é (posição Y do retrato + altura do retrato + 25px de padding)
            pos_nome_y = (pos_retrato_y + TAMANHO_RETRATO[1]) + 25 
            nome_surf = FONTES["TEXTO"].render(f.nome, True, CORES["BRANCO"])
            nome_rect = nome_surf.get_rect(center=(card_rect.centerx, pos_nome_y))
            surface.blit(nome_surf, nome_rect)

            # 4. Barras de Status (Posição Y Corrigida)
            stats = {
                "Determinação": (f.determinacao, CORES["GRAFICO_DETERMINACAO"]),
                "Respeito": (f.respeito, CORES["GRAFICO_RESPEITO"]),
                "Comodidade": (f.comodidade, CORES["GRAFICO_COMODIDADE"]),
                "Estresse": (f.estresse, CORES["GRAFICO_ESTRESSE"])
            }
            
            # Posição inicial Y (abaixo do nome)
            y_barra_atual = nome_rect.bottom + 15 
            
            barra_largura_max = card_rect.width - 60 
            pos_x_barra = card_rect.left + 30
            altura_barra = 15
            espaco_entre_barras = 7 # MUDANÇA: Espaço diminuído de 30 para 10

            for nome_stat, (valor, cor) in stats.items():
                rotulo_surf = FONTES["BOTAO"].render(nome_stat, True, CORES["BRANCO"])
                rotulo_rect = rotulo_surf.get_rect(left=pos_x_barra, top=y_barra_atual)
                surface.blit(rotulo_surf, rotulo_rect)
                
                y_barra = rotulo_rect.bottom + 5
                barra_rect = pygame.Rect(pos_x_barra, y_barra, barra_largura_max, altura_barra)
                
                desenhar_barra_status(surface, barra_rect, valor, 10, cor)

                # Incrementar a posição Y
                y_barra_atual = barra_rect.bottom + espaco_entre_barras 

        # --- 3. Botões de Conversar ---
        # (Posição já foi atualizada no __init__ e não sobrepõe mais a barra inferior)
        if self.lider_escolhido:
            tem_pa = self.lider_escolhido.pontos_acao > 0
            for nome, botao in self.botoes_conversar.items(): 
                botao.ativo = tem_pa and (nome not in self.funcionarios_conversados_hoje)
                botao.desenhar(surface, pos_mouse_hover)
        
        # --- 4. HUD Inferior (Barra de Ações) ---
        surface.blit(self.hud_bottom_surface, (0, ALTURA_TELA - 80))
        
        # Botão de Habilidade (Agora aparece)
        if self.botao_habilidade:
            # Centraliza o botão de habilidade na barra inferior
            self.botao_habilidade.rect.center = (LARGURA_TELA / 2, ALTURA_TELA - 40)
            self.botao_habilidade.desenhar(surface, pos_mouse_hover)

        # Botão Finalizar Dia (Movido para a barra inferior)
        self.botao_finalizar_dia.rect.center = (LARGURA_TELA - 160, ALTURA_TELA - 40) # Alinhado à direita
        self.botao_finalizar_dia.desenhar(surface, pos_mouse_hover)

        # Feedback (ex: "Sem PA")
        if self.feedback_timer > 0:
            fb_surf = FONTES["TEXTO"].render(self.feedback_texto, True, CORES["AMARELO"])
            # Posição Y movida para cima da barra inferior
            fb_rect = fb_surf.get_rect(center=(LARGURA_TELA/2, ALTURA_TELA - 110))
            surface.blit(fb_surf, fb_rect)
            self.feedback_timer -= 1
    
    def desenhar_tela_escolha(self, surface, pos_mouse_hover=(0,0)):
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        ts = FONTES["TITULO"].render("Escolha seu Arquétipo", True, CORES["BRANCO"]); surface.blit(ts, (LARGURA_TELA/2 - ts.get_width()/2, 50))
        for b in self.botoes_escolha_lider: b.desenhar(surface, pos_mouse_hover) # Passa o hover
        self.botao_sair.desenhar(surface, pos_mouse_hover) # Passa o hover

    def desenhar_tela_evento(self, surface, pos_mouse_hover=(0,0)):
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        # --- LAYOUT DE EVENTO ATUALIZADO (Dinâmico e Centralizado) ---
        
        # 1. Calcular altura do texto PRIMEIRO
        descricao_texto = f'"{self.evento_atual.descricao}"'
        font_desc = FONTES["DIALOGO"]
        # Largura da caixa (LARGURA_TELA - 80) - margens internas (60)
        largura_texto = (LARGURA_TELA - 80) - 60 
        
        altura_texto_calculada = calcular_altura_texto(descricao_texto, largura_texto, font_desc)
        
        # 2. Definir altura da caixa dinamicamente
        margem_vertical_titulo = 80 # Espaço para o título
        padding_vertical_caixa = 40 # Espaço abaixo do texto
        altura_caixa_dinamica = margem_vertical_titulo + altura_texto_calculada + padding_vertical_caixa
        
        # Posição Y centralizada para a nova altura
        pos_y_caixa = (ALTURA_TELA // 2) - (altura_caixa_dinamica // 2) - 50 # Sobe 50 para dar espaço aos botões
        
        caixa_dialogo_rect = pygame.Rect(40, pos_y_caixa, LARGURA_TELA - 80, altura_caixa_dinamica)
        pygame.draw.rect(surface, CORES["CINZA"], caixa_dialogo_rect, border_radius=10)

        # 3. Desenhar o Título (com símbolo de alarme)
        titulo_evento = f"[ ! ] {self.evento_atual.titulo} [ ! ]"
        titulo_surf = FONTES["TITULO"].render(titulo_evento, True, CORES["BRANCO"])
        titulo_rect = titulo_surf.get_rect(center=(caixa_dialogo_rect.centerx, caixa_dialogo_rect.top + 40))
        surface.blit(titulo_surf, titulo_rect)

        # 4. Definir o rect do texto e desenhar CENTRALIZADO
        rect_texto = pygame.Rect(
            caixa_dialogo_rect.left + 30, 
            caixa_dialogo_rect.top + margem_vertical_titulo, # Abaixo do título
            largura_texto, 
            altura_texto_calculada + 10 # +10 de 'folga'
        )
        desenhar_texto_multilinha(surface, descricao_texto, rect_texto, font_desc, CORES["BRANCO"], centralizado=True)
        
        # 5. Desenhar os botões do grid
        for b in self.botoes_evento: 
            b.desenhar(surface, pos_mouse_hover)

        self.botao_sair.desenhar(surface, pos_mouse_hover) # Passa o hover
        # --- FIM DA ATUALIZAÇÃO ---
    
    def desenhar_tela_relatorio(self, surface, pos_mouse_hover=(0,0)):
        fundo_key = 'fundo_sucesso' if self.resultado_final == "Sucesso" else 'fundo_fracasso'
        fundo = self.imagens.get(fundo_key, self.imagens.get('fundo_fabrica')) # Fallback to factory
        if fundo:
            surface.blit(fundo, (0,0))
        else:
            surface.fill(CORES["PRETO"]) # Fallback color

        if self.feedback_final_gerado is None: self.feedback_final_gerado = self.gerar_texto_analise()
        
        # Desenha a caixa com código
        caixa_rect = pygame.Rect(100, 50, LARGURA_TELA - 200, ALTURA_TELA - 100)
        pygame.draw.rect(surface, CORES["CINZA"], caixa_rect, border_radius=10)


        titulo_surf = FONTES["TITULO"].render("Relatório Final", True, CORES["BRANCO"])
        titulo_rect = titulo_surf.get_rect(center=(LARGURA_TELA / 2, caixa_rect.top + 40))
        surface.blit(titulo_surf, titulo_rect)
        
        y_texto = caixa_rect.top + 80 # Start text lower
        if self.feedback_final_gerado:
            subtitulo_surf = FONTES["TEXTO"].render(self.feedback_final_gerado.get('titulo', ''), True, CORES["AMARELO"])
            sub_rect = subtitulo_surf.get_rect(center=(LARGURA_TELA / 2, y_texto))
            surface.blit(subtitulo_surf, sub_rect); y_texto += 50

            textos_info = {
                 "Análise de Estilo:": 'analise_estilo',
                 "Análise de Eficácia:": 'analise_eficacia',
                 "Feedback para o Futuro:": 'feedback_futuro'
            }
            
            for titulo_str, key in textos_info.items():
                 # Draw section title
                 titulo_seccao = FONTES["TEXTO"].render(titulo_str, True, CORES["AZUL"])
                 surface.blit(titulo_seccao, (caixa_rect.left + 30, y_texto)); y_texto += 30
                 # Draw section text
                 rect_texto = pygame.Rect(caixa_rect.left + 30, y_texto, caixa_rect.width - 60, 90) # Adjust height as needed
                 desenhar_texto_multilinha(surface, self.feedback_final_gerado.get(key, ''), rect_texto, FONTES["BOTAO"], CORES["BRANCO"])
                 y_texto += 110 # Adjust spacing


        self.botao_sair.desenhar(surface, pos_mouse_hover) # Passa o hover

    def terminar_jogo(self, resultado):
        self.resultado_final = resultado
        self.estado_jogo = "TELA_RELATORIO_FINAL"

    # UPDATE: Rewritten analysis function for Situational Leadership
    def gerar_texto_analise(self):
        if not self.lider_escolhido or not self.banco_feedbacks: return None
        contadores = self.lider_escolhido.contadores
        
        # Calculate totals for each style
        total_determinar = contadores['determinar_eficaz'] + contadores['determinar_ineficaz']
        total_orientar = contadores['orientar_eficaz'] + contadores['orientar_ineficaz']
        total_apoiar = contadores['apoiar_eficaz'] + contadores['apoiar_ineficaz']
        total_delegar = contadores['delegar_eficaz'] + contadores['delegar_ineficaz']
        total_acoes = total_determinar + total_orientar + total_apoiar + total_delegar

        if total_acoes == 0:
            return {"titulo": "Análise Indisponível", "analise_estilo": "Nenhuma ação de diálogo realizada.", "analise_eficacia": "", "feedback_futuro": ""}

        # Determine predominant style
        estilos_usados = {
            "Determinar": total_determinar,
            "Orientar": total_orientar,
            "Apoiar": total_apoiar,
            "Delegar": total_delegar
        }
        # Find the style(s) with the maximum usage
        max_uso = max(estilos_usados.values())
        estilos_predominantes = [estilo for estilo, total in estilos_usados.items() if total == max_uso]

        estilo_feedback_key = "Equilibrado" # Default key for feedback lookup
        percentual_predominante = 0
        if max_uso > 0:
            percentual_predominante = (max_uso / total_acoes) * 100

        if len(estilos_predominantes) == 1:
            estilo_predominante_nome = estilos_predominantes[0]
            analise_estilo = f"Seu estilo predominante foi '{estilo_predominante_nome}', usado em {percentual_predominante:.0f}% das suas interações. "
            if percentual_predominante >= 50: # Threshold for clear predominance
                 analise_estilo += "Você demonstrou uma forte preferência por essa abordagem. "
                 estilo_feedback_key = estilo_predominante_nome # Use this specific style for feedback
            else:
                 analise_estilo += "Embora tenha sido o mais frequente, você variou seus estilos. "
                 # Keep estilo_feedback_key as "Equilibrado"
        else: # Multiple styles tied for most used
            estilos_str = " e ".join(estilos_predominantes)
            analise_estilo = f"Você utilizou uma mistura equilibrada de estilos, com '{estilos_str}' sendo os mais frequentes ({percentual_predominante:.0f}% cada). "
            estilo_feedback_key = "Equilibrado"

        # Calculate overall efficacy
        total_eficazes = contadores['determinar_eficaz'] + contadores['orientar_eficaz'] + contadores['apoiar_eficaz'] + contadores['delegar_eficaz']
        taxa_eficacia_geral = (total_eficazes / total_acoes) * 100 if total_acoes > 0 else 0 # Avoid division by zero


        analise_eficacia = f"Sua taxa de eficácia geral foi de {taxa_eficacia_geral:.0f}%. "
        if taxa_eficacia_geral >= 75: analise_eficacia += "Excelente leitura da equipe!"
        elif taxa_eficacia_geral >= 50: analise_eficacia += "Você foi eficaz na maioria das vezes."
        else: analise_eficacia += "Muitas intervenções não tiveram o efeito esperado. Busque adaptar melhor seu estilo."

        # Retrieve feedback text from feedbacks.json
        # IMPORTANT: feedbacks.json needs restructuring! Keys should be:
        # Sucesso/Fracasso -> Determinar/Orientar/Apoiar/Delegar/Equilibrado -> titulo/analise_estilo_base/feedback_futuro
        feedback_base = self.banco_feedbacks.get(self.resultado_final, {}).get(estilo_feedback_key, {})
        titulo = feedback_base.get('titulo', f"Resultado: {self.resultado_final} / Estilo: {estilo_feedback_key}")
        analise_estilo_base_txt = feedback_base.get('analise_estilo_base', "[Adapte feedbacks.json para incluir texto base da análise de estilo aqui]")
        feedback_futuro = feedback_base.get('feedback_futuro', "[Adapte feedbacks.json para incluir feedback futuro aqui]")

        # Combine generated analysis with base feedback text
        analise_estilo += analise_estilo_base_txt
        
        return {
            "titulo": titulo,
            "analise_estilo": analise_estilo,
            "analise_eficacia": analise_eficacia,
            "feedback_futuro": feedback_futuro
        }


    def avancar_dia(self, primeiro_dia=False):
         # Don't save status or generate points before the first day starts
        if not primeiro_dia:
            # Save status at the END of the day's actions
            for f in self.equipe: f.guardar_status_do_dia(self.projeto.dia_atual)
            # Calculate points generated based on status AT THE END of the day
            pontos_gerados = sum(max(0,f.determinacao-max(0,f.estresse-f.limiar_estresse))*1.5 for f in self.equipe)
            self.projeto.pontos_de_projeto += int(pontos_gerados)
            # Check for win condition
            if self.projeto.pontos_de_projeto >= self.projeto.meta_pontos: self.terminar_jogo("Sucesso"); return
            # Increment day only if not the first day processing
            self.projeto.dia_atual += 1
            # Check for lose condition (end of week)
            if self.projeto.dia_atual > 5: self.terminar_jogo("Fracasso"); return
        
        # --- Prepare for the START of the new day (or first day) ---
        if self.lider_escolhido:
            self.lider_escolhido.pontos_acao = self.lider_escolhido.max_pontos_acao
        self.funcionarios_conversados_hoje = []
        
        # Choose and display the event for the current day
        if self.banco_eventos:
            # Cycle through the 5 events based on the day number (1-5)
            # Ensure banco_eventos has at least 5 events
            num_eventos = len(self.banco_eventos)
            if num_eventos > 0:
                evento_idx = (self.projeto.dia_atual - 1) % num_eventos
                self.evento_atual = self.banco_eventos[evento_idx]
                self.id_evento_do_dia = self.evento_atual.id_evento # Store the ID
                
                # MUDANÇA: Chama a nova função para criar os botões no layout de grid
                self.criar_botoes_evento() 
                self.estado_jogo = "TELA_EVENTO"
            else:
                 print("AVISO: Banco de eventos vazio!")
                 self.estado_jogo = "JOGO_PRINCIPAL" # Skip event screen if no events
        else:
             self.estado_jogo = "JOGO_PRINCIPAL" # Skip event screen if banco_eventos is None


# =========================================================================
# 5. LOOP PRINCIPAL DO JOGO
# =========================================================================

def main():
    clock = pygame.time.Clock(); game_manager = GameManager()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game_manager.processar_input(event)
        
        game_manager.desenhar(tela); pygame.display.flip(); clock.tick(60)

if __name__ == '__main__':
    main()

