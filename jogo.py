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
CORES = {"PRETO": (0,0,0), "BRANCO": (255,255,255), "AZUL": (100,149,237), "VERDE": (60,179,113), "VERMELHO": (205,92,92), "CINZA": (40,40,40), "CINZA_CLARO": (100,100,100), "AMARELO": (255,215,0), "ROXO": (148,0,211), "GRAFICO_RESPEITO": (255, 215, 0), "GRAFICO_DETERMINACAO": (102, 255, 102), "GRAFICO_ESTRESSE": (255, 102, 102), "GRAFICO_COMODIDADE": (102, 178, 255)}

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

def desenhar_texto_multilinha(surface, text, rect, font, color):
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
            img = font.render(linha, True, color); surface.blit(img, (rect.left + 5, y)); y += font.get_linesize()

def desenhar_barra_status(surface, rect, valor_atual, valor_max=10, cor_cheia=(60,179,113), cor_vazia=(40,40,40)):
    # Desenha a barra "vazia" (fundo)
    pygame.draw.rect(surface, cor_vazia, rect, border_radius=3)
    # Calcula a largura da barra "cheia"
    largura_cheia = (valor_atual / valor_max) * rect.width
    if largura_cheia > 0:
        # Desenha a barra "cheia" por cima
        rect_cheia = pygame.Rect(rect.left, rect.top, largura_cheia, rect.height)
        pygame.draw.rect(surface, cor_cheia, rect_cheia, border_radius=3)
           

class Botao:
    def __init__(self, x, y, l, a, t="", cor=CORES["CINZA_CLARO"], ativo=True):
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
            # Lógica de Hover: Muda a cor se o mouse estiver em cima
            cor_atual = self.cor_fundo
            if self.ativo and self.rect.collidepoint(pos_mouse_hover):
                cor_atual = CORES["AZUL"] # Cor de Hover
            
            cor_desenho = cor_atual if self.ativo else CORES["CINZA"]; 
            pygame.draw.rect(surface, cor_desenho, self.rect, border_radius=5)

        if self.texto:
            # Cor do texto é sempre branca se não for imagem
            cor_texto = CORES["BRANCO"]
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
        self.botao_sair = Botao(LARGURA_TELA - 120, 20, 100, 40, "Sair", CORES["VERMELHO"])
        self.evento_atual = None; self.botoes_evento = []
        self.no_dialogo_atual = None; self.botoes_dialogo = []; self.funcionario_em_dialogo = None
        
        self.card_rects = [pygame.Rect(40 + i * 310, 150, 280, 440) for i in range(len(self.equipe))]
        self.botoes_conversar = {f.nome: Botao(self.card_rects[i].centerx - 90, self.card_rects[i].bottom + 10, 180, 50) for i, f in enumerate(self.equipe)}

        self.funcionarios_conversados_hoje = []
        self.botao_habilidade = None; self.feedback_texto = ""; self.feedback_timer = 0
        self.resultado_final = ""; self.feedback_final_gerado = None
        
        # Store the current day's event ID
        self.id_evento_do_dia = None
        
    def carregar_todas_imagens(self):
        imagens = {}
        nomes = ["bruno", "julia", "carlos", "sandra"]
        humores = ["neutro", "determinado", "estressado", "acomodado"]
        
        try:
            # Fundos e UI
            imagens['fundo_fabrica'] = pygame.transform.scale(pygame.image.load("assets/fundo_fabrica.png").convert(), (LARGURA_TELA, ALTURA_TELA))
            imagens['caixa_dialogo'] = pygame.image.load("assets/caixa_dialogo.png").convert_alpha()

            
            
            # Botões
            imagens['botao_conversar_ativo'] = pygame.image.load("assets/botao_conversar_ativo.png").convert_alpha()
            imagens['botao_conversar_inativo'] = pygame.image.load("assets/botao_conversar_inativo.png").convert_alpha()
            imagens['botao_fundo'] = pygame.image.load("assets/botao_fundo.png").convert_alpha()
            
            # --- ATUALIZADO: Carregar RETRATOS em vez de cards completos ---
            for nome_arquivo in nomes:
                imagens[nome_arquivo] = {}
                for humor in humores:
                    # O nome do arquivo agora é o RETRATO com fundo transparente
                    caminho = f"assets/{nome_arquivo}_retrato_{humor}.png"
                    imagens[nome_arquivo][humor] = pygame.image.load(caminho).convert_alpha()
            # Fundos de relatório
            imagens['fundo_sucesso'] = pygame.transform.scale(pygame.image.load("assets/fundo_sucesso.png").convert(), (LARGURA_TELA, ALTURA_TELA))
            imagens['fundo_fracasso'] = pygame.transform.scale(pygame.image.load("assets/fundo_fracasso.png").convert(), (LARGURA_TELA, ALTURA_TELA))

        except pygame.error as e:
            print(f"Erro ao carregar imagem: {e}. Verifique a pasta 'assets' e os nomes dos arquivos.")
        return imagens

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
        largura_botao, altura_botao = 450, 75 # Adjusted size slightly
        num_opcoes = len(opcoes)
        # Adjust vertical spacing based on number of options
        espacamento_vertical = altura_botao + (20 if num_opcoes <= 3 else 15)
        pos_y_inicial = ALTURA_TELA - (num_opcoes * espacamento_vertical) - 30 # Position from bottom

        for i, o in enumerate(opcoes):
            pos_x = (LARGURA_TELA - largura_botao) / 2
            pos_y = pos_y_inicial + i * espacamento_vertical
            self.botoes_dialogo.append(Botao(pos_x, pos_y, largura_botao, altura_botao, o.texto_resposta))


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
        
        
    def desenhar_tela_dialogo(self, surface, pos_mouse_hover): # Aceita pos_mouse_hover
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        if self.imagens.get('caixa_dialogo'):
            caixa_img = self.imagens.get('caixa_dialogo')
            caixa_rect = caixa_img.get_rect(center=(LARGURA_TELA / 2, 150)) # Position caixa higher
            surface.blit(caixa_img, caixa_rect)

        titulo_surf = FONTES["TITULO"].render(f"Conversando com: {self.funcionario_em_dialogo.nome}", True, CORES["BRANCO"])
        titulo_rect = titulo_surf.get_rect(center=(LARGURA_TELA / 2, caixa_rect.top + 40)) # Adjust title pos
        surface.blit(titulo_surf, titulo_rect)

        rect = pygame.Rect(caixa_rect.left + 30, caixa_rect.top + 70, caixa_rect.width - 60, caixa_rect.height - 90); 
        desenhar_texto_multilinha(surface, f'"{self.no_dialogo_atual.frase_abertura}"', rect, FONTES["DIALOGO"], CORES["BRANCO"]) # Adjust text pos
        
        # --- ATUALIZADO: Passa pos_mouse_hover e remove 'botao_fundo' ---
        for b in self.botoes_dialogo: b.desenhar(surface, pos_mouse_hover)
        self.botao_sair.desenhar(surface, pos_mouse_hover)



    def desenhar_hud_jogo(self, surface, pos_mouse_hover): # Aceita pos_mouse_hover
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        # HUD Superior
        dia_surf = FONTES["TEXTO"].render(f"Dia: {self.projeto.get_dia_semana()}", True, CORES["BRANCO"])
        surface.blit(dia_surf, (50, 20))
        pontos_surf = FONTES["TEXTO"].render(f"Pontos: {self.projeto.pontos_de_projeto}/{self.projeto.meta_pontos}", True, CORES["BRANCO"])
        surface.blit(pontos_surf, (LARGURA_TELA - pontos_surf.get_width() - 50, 20))
        if self.lider_escolhido:
            pa_surf = FONTES["TEXTO"].render(f"PA: {self.lider_escolhido.pontos_acao}", True, CORES["AMARELO"])
            surface.blit(pa_surf, (LARGURA_TELA/2 - pa_surf.get_width()/2, 20))
        
        # Cards dos Funcionários
        for i, f in enumerate(self.equipe):
            card_rect = self.card_rects[i]
            
            # --- ATUALIZADO: Montagem dinâmica com fundo por código e escala de imagem ---
            
            
            # 1. Desenhar o fundo do card (Sua ideia!)
            # Usa a cor CINZA (40,40,40) como fundo. Mude se quiser.
            pygame.draw.rect(surface, CORES["CINZA"], card_rect, border_radius=10)

            # 2. Definir tamanho padrão e desenhar o Retrato
            nome_arquivo = f.nome.lower().replace('ú', 'u')
            humor = self.get_humor_funcionario(f)
            
            retrato_rect = pygame.Rect(0,0,0,0) # Inicializa
            
            if nome_arquivo in self.imagens and humor in self.imagens[nome_arquivo]:
                retrato_img_original = self.imagens[nome_arquivo][humor]
                
                # --- A MÁGICA ESTÁ AQUI ---
                # Define o tamanho padrão para todos os retratos
                TAMANHO_RETRATO = (240, 220) # (Largura, Altura) - Ajuste se precisar
                try:
                    retrato_img_scaled = pygame.transform.scale(retrato_img_original, TAMANHO_RETRATO)
                except Exception as e:
                    print(f"Erro ao redimensionar {nome_arquivo}: {e}")
                    retrato_img_scaled = pygame.Surface(TAMANHO_RETRATO) # Cria um fallback
                    retrato_img_scaled.fill(CORES["ROXO"]) # Cor de erro
                
                # Posiciona o retrato (agora redimensionado) centralizado na parte de cima
                retrato_rect = retrato_img_scaled.get_rect(centerx=card_rect.centerx, top=card_rect.top + 20)
                surface.blit(retrato_img_scaled, retrato_rect)
            # --- Fim da Mágica (Fim do Bloco IF) ---

            # 3. Desenhar o Nome do Funcionário (abaixo do retrato)
            # --- CORRIGIDO: Este bloco agora está FORA do IF acima ---
            nome_surf = FONTES["TEXTO"].render(f.nome, True, CORES["BRANCO"])
            nome_rect = nome_surf.get_rect(centerx=card_rect.centerx, top=retrato_rect.bottom + 10)
            surface.blit(nome_surf, nome_rect)

            # 4. Desenhar as Barras de Status (abaixo do nome)
            # A posição Y agora é dinâmica, baseada no nome
            y_stats_start = nome_rect.bottom + 20 # Ponto de partida vertical
            barra_largura = 110 # Largura da barra
            barra_altura = 12   # Altura da barra
            
            pos_x_col1 = card_rect.left + 20
            pos_x_col2 = card_rect.left + 150
            
            y_linha1_texto = y_stats_start
            y_linha1_barra = y_linha1_texto + 15 # Barra abaixo do texto
            
            y_linha2_texto = y_stats_start + 35 # Próxima linha
            y_linha2_barra = y_linha2_texto + 15

            # --- Barra de Determinação (Linha 1, Col 1) ---
            texto_det = FONTES["BOTAO"].render("Determin.", True, CORES["BRANCO"])
            surface.blit(texto_det, (pos_x_col1, y_linha1_texto))
            barra_det_rect = pygame.Rect(pos_x_col1, y_linha1_barra, barra_largura, barra_altura)
            desenhar_barra_status(surface, barra_det_rect, f.determinacao, 10, CORES["GRAFICO_DETERMINACAO"], CORES["CINZA"])

            # --- Barra de Respeito (Linha 1, Col 2) ---
            texto_res = FONTES["BOTAO"].render("Respeito", True, CORES["BRANCO"])
            surface.blit(texto_res, (pos_x_col2, y_linha1_texto))
            barra_res_rect = pygame.Rect(pos_x_col2, y_linha1_barra, barra_largura, barra_altura)
            desenhar_barra_status(surface, barra_res_rect, f.respeito, 10, CORES["GRAFICO_RESPEITO"], CORES["CINZA"])

            # --- Barra de Comodidade (Linha 2, Col 1) ---
            texto_com = FONTES["BOTAO"].render("Comodid.", True, CORES["BRANCO"])
            surface.blit(texto_com, (pos_x_col1, y_linha2_texto))
            barra_com_rect = pygame.Rect(pos_x_col1, y_linha2_barra, barra_largura, barra_altura)
            desenhar_barra_status(surface, barra_com_rect, f.comodidade, 10, CORES["GRAFICO_COMODIDADE"], CORES["CINZA"])
            
            # --- Barra de Estresse (Linha 2, Col 2) ---
            texto_str = FONTES["BOTAO"].render("Estresse", True, CORES["BRANCO"])
            surface.blit(texto_str, (pos_x_col2, y_linha2_texto))
            barra_str_rect = pygame.Rect(pos_x_col2, y_linha2_barra, barra_largura, barra_altura)
            desenhar_barra_status(surface, barra_str_rect, f.estresse, 10, CORES["GRAFICO_ESTRESSE"], CORES["CINZA"])
            # --- Fim da atualização ---  

            stats = {
                "Determinacao": (f.determinacao, CORES["GRAFICO_DETERMINACAO"]),
                "Respeito": (f.respeito, CORES["GRAFICO_RESPEITO"]),
                "Comodidade": (f.comodidade, CORES["GRAFICO_COMODIDADE"]),
                "Stress": (f.estresse, CORES["GRAFICO_ESTRESSE"])
            }
            
            y_offset = card_rect.height - 85
            for j, (nome_stat, (valor, cor)) in enumerate(stats.items()):
                pos_texto = (card_rect.left + 20, card_rect.top + y_offset + (j // 2) * 35)
                pos_circulo = (card_rect.left + 240, card_rect.top + y_offset + (j // 2) * 35 + 8)
                
                if j % 2 != 0: 
                    pos_texto = (card_rect.left + 150, card_rect.top + y_offset + (j // 2) * 35)
                    pos_circulo = (card_rect.left + 260, card_rect.top + y_offset + (j // 2) * 35 + 8)

                texto_surf = FONTES["BOTAO"].render(f"{nome_stat} {valor}", True, CORES["BRANCO"])
                surface.blit(texto_surf, pos_texto)
                pygame.draw.circle(surface, cor, pos_circulo, 7)

        # Botões de Conversar
        if self.lider_escolhido:
            tem_pa = self.lider_escolhido.pontos_acao > 0
            for nome, botao in self.botoes_conversar.items(): 
                botao.ativo = tem_pa and (nome not in self.funcionarios_conversados_hoje)
                botao.desenhar(surface, self.imagens.get('botao_conversar_ativo'), self.imagens.get('botao_conversar_inativo'))
        
        self.botao_finalizar_dia.desenhar(surface, pos_mouse_hover)
        self.botao_sair.desenhar(surface, pos_mouse_hover)

        if self.feedback_timer > 0:
            fb_surf = FONTES["TEXTO"].render(self.feedback_texto, True, CORES["AMARELO"]); surface.blit(fb_surf, (LARGURA_TELA/2 - fb_surf.get_width()/2, ALTURA_TELA-150)); self.feedback_timer -= 1
    
    def desenhar_tela_escolha(self, surface, pos_mouse_hover): # Aceita pos_mouse_hover
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        ts = FONTES["TITULO"].render("Escolha seu Arquétipo", True, CORES["BRANCO"]); surface.blit(ts, (LARGURA_TELA/2 - ts.get_width()/2, 50))
        for b in self.botoes_escolha_lider: b.desenhar(surface, pos_mouse_hover)
        self.botao_sair.desenhar(surface, pos_mouse_hover)

    def desenhar_tela_evento(self, surface, pos_mouse_hover): # Aceita pos_mouse_hover
        surface.blit(self.imagens.get('fundo_fabrica'), (0,0))
        
        caixa_img = self.imagens.get('caixa_dialogo')
        # Define caixa_rect COM a imagem OU com fallback ANTES de usar
        if caixa_img:
             caixa_rect = caixa_img.get_rect(center=(LARGURA_TELA / 2, 200)) # Center event box
             surface.blit(caixa_img, caixa_rect)
        else:
             # Define caixa_rect com as dimensões do fallback se a imagem falhar
             caixa_rect = pygame.Rect(0, 0, LARGURA_TELA - 200, 300) # Exemplo: Largura da tela - margens, Altura fixa
             caixa_rect.center = (LARGURA_TELA / 2, 200)
             pygame.draw.rect(surface, CORES["CINZA"], caixa_rect, border_radius=10) # Desenha o fallback
        
        titulo_surf = FONTES["TITULO"].render(self.evento_atual.titulo, True, CORES["BRANCO"])
        titulo_rect = titulo_surf.get_rect(center=(LARGURA_TELA / 2, caixa_rect.top + 40)) # Position title inside
        surface.blit(titulo_surf, titulo_rect)
        
        rect_desc = pygame.Rect(caixa_rect.left + 30, caixa_rect.top + 70, caixa_rect.width - 60, caixa_rect.height - 120); 
        desenhar_texto_multilinha(surface, f'"{self.evento_atual.descricao}"', rect_desc, FONTES["DIALOGO"], CORES["BRANCO"]) # Position desc inside
        
        # Position buttons below the event box (agora caixa_rect sempre existe)
        for i, b in enumerate(self.botoes_evento):
             b.rect.width = LARGURA_TELA - 300 # Define a largura aqui também
             b.rect.height = 70              # Define a altura aqui também
             b.rect.centerx = LARGURA_TELA / 2
             b.rect.top = caixa_rect.bottom + 20 + i * (b.rect.height + 15)
             # --- ATUALIZADO: Passa pos_mouse_hover e remove 'botao_fundo' ---
             b.desenhar(surface, pos_mouse_hover)

        self.botao_sair.desenhar(surface, pos_mouse_hover)
    
    def desenhar_tela_relatorio(self, surface, pos_mouse_hover): # Aceita pos_mouse_hover
        fundo_key = 'fundo_sucesso' if self.resultado_final == "Sucesso" else 'fundo_fracasso'
        fundo = self.imagens.get(fundo_key, self.imagens.get('fundo_fabrica')) # Fallback to factory
        if fundo:
            surface.blit(fundo, (0,0))
        else:
            surface.fill(CORES["PRETO"]) # Fallback color

        if self.feedback_final_gerado is None: self.feedback_final_gerado = self.gerar_texto_analise()
        
        caixa_img = self.imagens.get('caixa_dialogo')
        if caixa_img:
            caixa_rect = caixa_img.get_rect(center=(LARGURA_TELA / 2, ALTURA_TELA / 2))
            surface.blit(caixa_img, caixa_rect)
        else: # Fallback rectangle if image is missing
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


        self.botao_sair.desenhar(surface, pos_mouse_hover)

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
                
                # Create buttons for the event screen
                self.botoes_evento = [Botao(0, 0, LARGURA_TELA-300, 70, o.texto_resposta) for i, o in enumerate(self.evento_atual.opcoes)] # Adjusted size
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

