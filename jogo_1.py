# Parceiro de Programacao: Projeto Prisma - Fase 12 (Sistema de Estados Narrativos)

import pygame
import sys
import re
import random
import json

pygame.init()

# --- Constantes e Configuração ---
LARGURA_TELA, ALTURA_TELA = 1280, 720
NOME_JOGO = "Projeto Prisma: Simulação de Liderança"
CORES = {"PRETO": (0,0,0), "BRANCO": (255,255,255), "AZUL": (100,149,237), "VERDE": (60,179,113), "VERMELHO": (205,92,92), "CINZA": (40,40,40), "CINZA_CLARO": (100,100,100), "AMARELO": (255,215,0), "ROXO": (148,0,211), "GRAFICO_RESPEITO": (102, 255, 102), "GRAFICO_DETERMINACAO": (102, 178, 255), "GRAFICO_ESTRESSE": (255, 102, 102), "GRAFICO_COMODIDADE": (255, 255, 102)}
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
        self.flags_narrativas = set() # A "memória" do funcionário
    def guardar_status_do_dia(self, dia):
        self.historico_status.append({"dia": dia, "respeito": self.respeito, "determinacao": self.determinacao, "estresse": self.estresse, "comodidade": self.comodidade})
    def adicionar_flag(self, flag):
        if flag: self.flags_narrativas.add(flag); print(f"Flag '{flag}' adicionada para {self.nome}.")
    def remover_flag(self, flag):
        if flag and flag in self.flags_narrativas:
            self.flags_narrativas.remove(flag); print(f"Flag '{flag}' removida de {self.nome}.")

class Lider:
    def __init__(self, nome, dados):
        self.nome = nome
        self.descricao = dados.get('descricao', '')
        self.pontos_acao = 3; self.max_pontos_acao = 3
        self.habilidade_nome = dados.get('habilidade_nome', 'Nenhuma')
        self.habilidade_custo = dados.get('habilidade_custo', 0)
        self.habilidade_requer_alvo = dados.get('habilidade_requer_alvo', False)
        self.contadores = {"apoio_eficaz": 0, "apoio_ineficaz": 0, "pressao_eficaz": 0, "pressao_ineficaz": 0}
    def aplicar_passiva(self, equipe): pass
    def usar_habilidade_ativa(self, game_manager, alvo=None): return False

class DiretorAutocrata(Lider):
    def aplicar_passiva(self, equipe):
        for f in equipe:
            if f.geracao == "Baby Boomer": f.respeito += 2
            elif f.geracao == "Geração Z": f.respeito -= 2
    def usar_habilidade_ativa(self, game_manager, alvo):
        if alvo: self.contadores["pressao_eficaz"] += 1; game_manager.modificar_status(alvo, "estresse", 2); game_manager.modificar_status(alvo, "pontos_de_projeto", 20); return True
        return False

class VisionarioTransformacional(Lider):
    def aplicar_passiva(self, equipe):
        for f in equipe:
            if f.geracao == "Millennial": f.respeito += 2
    def usar_habilidade_ativa(self, game_manager, alvo=None):
        self.contadores["apoio_eficaz"] += 1
        for f in game_manager.equipe: game_manager.modificar_status(f, "determinacao", 2)
        return True

class LiderServidor(Lider):
    def usar_habilidade_ativa(self, game_manager, alvo):
        if alvo: self.contadores["apoio_eficaz"] += 1; game_manager.modificar_status(alvo, "estresse", -3); return True
        return False

class OpcaoDialogo:
    def __init__(self, texto, efeitos, tipo, eficacia, adicionar_flag=None, remover_flag=None):
        self.texto_resposta = texto
        self.efeitos = efeitos
        self.tipo = tipo
        self.eficacia = eficacia
        self.adicionar_flag = adicionar_flag
        self.remover_flag = remover_flag

class NoDialogo:
    def __init__(self, frase, lista_de_opcoes):
        self.frase_abertura = frase
        self.opcoes = lista_de_opcoes

class Evento:
    def __init__(self, titulo, desc, op1_txt, op1_ef, op2_txt, op2_ef):
        self.titulo, self.descricao = titulo, desc
        self.opcoes = [OpcaoDialogo(op1_txt, op1_ef, "neutro", "neutro"), OpcaoDialogo(op2_txt, op2_ef, "neutro", "neutro")]

def parse_efeitos(texto):
    if not texto: return []
    mapa = {"Respeito": "respeito", "Comodidade": "comodidade", "Projeto": "pontos_de_projeto", "Estresse": "estresse", "Determinação": "determinacao"}
    efeitos = []
    matches = re.findall(r"(\w+)\s*([+-])(\d+)", texto)
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
    y = rect.top + 10
    for linha in linhas:
        if linha.strip():
            img = font.render(linha, True, color); surface.blit(img, (rect.left + 10, y)); y += font.get_linesize()

class Botao:
    def __init__(self, x, y, l, a, t, cor=CORES["CINZA_CLARO"], ativo=True):
        self.rect = pygame.Rect(x, y, l, a); self.texto, self.cor_fundo, self.ativo = t, cor, ativo
    def desenhar(self, surface):
        cor = self.cor_fundo if self.ativo else CORES["CINZA"]; pygame.draw.rect(surface, cor, self.rect, border_radius=5)
        desenhar_texto_multilinha(surface, self.texto, self.rect, FONTES["BOTAO"], CORES["PRETO"])
    def foi_clicado(self, pos): return self.ativo and self.rect.collidepoint(pos)

# =========================================================================
# 3. CONTEÚDO DO JOGO (Carregado de ficheiros externos)
# =========================================================================

def carregar_banco_dialogos_de_json(nome_ficheiro):
    banco = {}
    try:
        with open(f"gamedata/{nome_ficheiro}", 'r', encoding='utf-8') as f:
            dados = json.load(f)
            for item in dados:
                dia, gatilho = item['dia'], item['gatilho']
                lista_opcoes = []
                for opt in item.get('opcoes', []):
                    efeitos = parse_efeitos(opt.get('efeito', ''))
                    tipo = opt.get('tipo', 'neutro')
                    eficacia = opt.get('eficacia', 'neutro')
                    add_flag = opt.get('adicionar_flag')
                    rem_flag = opt.get('remover_flag')
                    lista_opcoes.append(OpcaoDialogo(opt.get('texto', ''), efeitos, tipo, eficacia, add_flag, rem_flag))
                banco.setdefault(dia, {})[gatilho] = NoDialogo(item['frase'], lista_opcoes)
    except FileNotFoundError: print(f"AVISO: Ficheiro 'gamedata/{nome_ficheiro}' não encontrado."); return {}
    except Exception as e: print(f"ERRO ao carregar '{nome_ficheiro}': {e}"); return {}
    return banco

def carregar_dados_json(nome_ficheiro):
    try:
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
        dados_equipe = carregar_dados_json("equipe.json") or []
        status_base = {"respeito": 5, "determinacao": 7, "estresse": 3, "comodidade": 2}
        self.equipe = [Funcionario(d['nome'], d['geracao'], status_base) for d in dados_equipe]
        
        dados_lideres = carregar_dados_json("lideres.json") or {}
        self.arquetipos_disponiveis = []
        for nome, dados in dados_lideres.items():
            if nome == "Diretor Autocrata": self.arquetipos_disponiveis.append(DiretorAutocrata(nome, dados))
            elif nome == "Visionário Transformacional": self.arquetipos_disponiveis.append(VisionarioTransformacional(nome, dados))
            elif nome == "Líder Servidor": self.arquetipos_disponiveis.append(LiderServidor(nome, dados))

        self.banco_dialogos = {f.nome: carregar_banco_dialogos_de_json(f"{f.nome.lower()}.json") for f in self.equipe}
        self.banco_eventos = [Evento(e['titulo'], e['desc'], e['op1_txt'], parse_efeitos(e['op1_ef']), e['op2_txt'], parse_efeitos(e['op2_ef'])) for e in (carregar_dados_json("eventos.json") or [])]
        self.banco_feedbacks = carregar_dados_json("feedbacks.json") or {}

        self.lider_escolhido = None
        self.botoes_escolha_lider = [Botao(LARGURA_TELA/2-175, 150+i*100, 350, 70, a.nome) for i, a in enumerate(self.arquetipos_disponiveis)]
        self.botao_finalizar_dia = Botao(LARGURA_TELA-250, ALTURA_TELA-70, 200, 50, "Finalizar Dia")
        self.botao_sair = Botao(LARGURA_TELA - 120, 20, 100, 40, "Sair", CORES["VERMELHO"])
        self.evento_atual = None; self.botoes_evento = []
        self.no_dialogo_atual = None; self.botoes_dialogo = []; self.funcionario_em_dialogo = None
        self.botoes_conversar = {f.nome: Botao(500, 120 + (i*120)+35, 180, 40, "Conversar (1 PA)", CORES["AMARELO"]) for i, f in enumerate(self.equipe)}
        self.funcionarios_conversados_hoje = []
        self.botao_habilidade = None; self.feedback_texto = ""; self.feedback_timer = 0
        self.resultado_final = ""; self.feedback_final_gerado = None
        
    def processar_input(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN: return
        pos_mouse = event.pos
        if self.botao_sair.foi_clicado(pos_mouse): pygame.quit(); sys.exit()

        if self.estado_jogo == "TELA_DE_ESCOLHA":
            for i, botao in enumerate(self.botoes_escolha_lider):
                if botao.foi_clicado(pos_mouse): self.lider_escolhido = self.arquetipos_disponiveis[i]; self.lider_escolhido.aplicar_passiva(self.equipe); self.botao_habilidade = Botao(LARGURA_TELA-500, ALTURA_TELA-70, 220, 50, f"{self.lider_escolhido.habilidade_nome} ({self.lider_escolhido.habilidade_custo} PA)", CORES["ROXO"]); self.estado_jogo = "JOGO_PRINCIPAL"
        elif self.estado_jogo == "MODO_ALVO":
            alvo = next((f for i, f in enumerate(self.equipe) if pygame.Rect(50, 120 + i*120, 400, 100).collidepoint(pos_mouse)), None)
            if alvo:
                if self.lider_escolhido.usar_habilidade_ativa(self, alvo): self.lider_escolhido.pontos_acao -= self.lider_escolhido.habilidade_custo
            else: self.mostrar_feedback("Seleção de alvo cancelada.")
            self.estado_jogo = "JOGO_PRINCIPAL"
        elif self.estado_jogo == "TELA_EVENTO":
            for i, botao in enumerate(self.botoes_evento):
                if botao.foi_clicado(pos_mouse): self.aplicar_efeitos(self.evento_atual.opcoes[i].efeitos); self.estado_jogo = "JOGO_PRINCIPAL"
        elif self.estado_jogo == "TELA_DIALOGO":
            for i, botao in enumerate(self.botoes_dialogo):
                if botao.foi_clicado(pos_mouse):
                    opcao = self.no_dialogo_atual.opcoes[i]
                    contador_key = f"{opcao.tipo}_{opcao.eficacia}"
                    if contador_key in self.lider_escolhido.contadores:
                        self.lider_escolhido.contadores[contador_key] += 1
                    if opcao.adicionar_flag: self.funcionario_em_dialogo.adicionar_flag(opcao.adicionar_flag)
                    if opcao.remover_flag: self.funcionario_em_dialogo.remover_flag(opcao.remover_flag)
                    self.aplicar_efeitos(opcao.efeitos, self.funcionario_em_dialogo); self.estado_jogo = "JOGO_PRINCIPAL"
        elif self.estado_jogo == "JOGO_PRINCIPAL":
            for nome, botao in self.botoes_conversar.items():
                if botao.foi_clicado(pos_mouse): self.iniciar_dialogo(nome)
            if self.botao_habilidade and self.botao_habilidade.foi_clicado(pos_mouse):
                h = self.lider_escolhido
                if h.pontos_acao >= h.habilidade_custo:
                    if h.habilidade_requer_alvo: self.estado_jogo = "MODO_ALVO"; self.mostrar_feedback(f"Selecione o alvo para '{h.habilidade_nome}'...")
                    else:
                        if h.usar_habilidade_ativa(self): h.pontos_acao -= h.habilidade_custo
                else: self.mostrar_feedback("Pontos de Ação insuficientes!")
            if self.botao_finalizar_dia.foi_clicado(pos_mouse): self.avancar_dia()
        elif self.estado_jogo == "TELA_RELATORIO_FINAL":
            pass

    def iniciar_dialogo(self, nome_funcionario):
        if not self.lider_escolhido or self.lider_escolhido.pontos_acao < 1: print("Sem PA."); return
        if nome_funcionario in self.funcionarios_conversados_hoje: print(f"Já conversou com {nome_funcionario} hoje."); return
        self.lider_escolhido.pontos_acao -= 1; self.funcionarios_conversados_hoje.append(nome_funcionario)
        self.funcionario_em_dialogo = next((f for f in self.equipe if f.nome == nome_funcionario), None)
        if not self.funcionario_em_dialogo: return
        dia = self.projeto.get_dia_semana(); dialogos = self.banco_dialogos.get(nome_funcionario, {}).get(dia)
        if not dialogos:
            print(f"AVISO: Nenhum diálogo para {nome_funcionario} na {dia}."); self.funcionarios_conversados_hoje.pop(); self.lider_escolhido.pontos_acao += 1; return
        f = self.funcionario_em_dialogo
        
        for flag in list(f.flags_narrativas):
            gatilho_flag = f"FLAG_{flag}"
            if gatilho_flag in dialogos:
                self.no_dialogo_atual = dialogos[gatilho_flag]
                print(f"Diálogo com {f.nome} (Gatilho de Flag: {gatilho_flag})"); self.criar_botoes_dialogo(); self.estado_jogo = "TELA_DIALOGO"; return

        if "Padrão" in dialogos:
            self.no_dialogo_atual = dialogos["Padrão"]
            self.criar_botoes_dialogo()
            self.estado_jogo = "TELA_DIALOGO"
            print(f"Diálogo com {f.nome} (Gatilho: Padrão)")
            return

    def criar_botoes_dialogo(self):
        self.botoes_dialogo = []
        opcoes_para_mostrar = list(self.no_dialogo_atual.opcoes)
        random.shuffle(opcoes_para_mostrar)
        self.no_dialogo_atual.opcoes = opcoes_para_mostrar
        largura_botao = (LARGURA_TELA-250)/2; altura_botao = 80; pos_inicial_y = 350
        for i, o in enumerate(self.no_dialogo_atual.opcoes):
            pos_x = 100 + (i%2)*(largura_botao+50); pos_y = pos_inicial_y + (i//2)*(altura_botao+30)
            self.botoes_dialogo.append(Botao(pos_x, pos_y, largura_botao, altura_botao, o.texto_resposta))

    def aplicar_efeitos(self, efeitos, alvo_especifico=None):
        alvos = [alvo_especifico] if alvo_especifico else self.equipe
        for efeito in efeitos:
            for alvo in alvos:
                if alvo: self.modificar_status(alvo, efeito['atributo'], efeito['valor'])

    def modificar_status(self, funcionario, atributo, valor):
        if atributo == "pontos_de_projeto":
            self.projeto.pontos_de_projeto += valor
            print(f"  - Projeto: {atributo} para {self.projeto.pontos_de_projeto}.")
        else:
            setattr(funcionario, atributo, max(0, min(10, getattr(funcionario, atributo) + valor)))
            print(f"  - {funcionario.nome}: {atributo} para {getattr(funcionario, atributo)}.")

    def mostrar_feedback(self, texto, duracao=120): self.feedback_texto = texto; self.feedback_timer = duracao
    
    def desenhar(self, surface):
        mapa = {"TELA_DE_ESCOLHA": self.desenhar_tela_escolha, "TELA_EVENTO": self.desenhar_tela_evento, "TELA_DIALOGO": self.desenhar_tela_dialogo, "MODO_ALVO": self.desenhar_hud_jogo, "TELA_RELATORIO_FINAL": self.desenhar_tela_relatorio}
        desenho_func = mapa.get(self.estado_jogo, self.desenhar_hud_jogo); desenho_func(surface)
        
    def desenhar_tela_escolha(self, surface):
        surface.fill(CORES["PRETO"]); ts = FONTES["TITULO"].render("Escolha seu Arquétipo de Liderança", True, CORES["BRANCO"]); surface.blit(ts, (LARGURA_TELA/2 - ts.get_width()/2, 50))
        for b in self.botoes_escolha_lider: b.desenhar(surface)
        self.botao_sair.desenhar(surface)

    def desenhar_tela_evento(self, surface):
        surface.fill(CORES["CINZA"]); surface.blit(FONTES["TITULO"].render(self.evento_atual.titulo, True, CORES["AMARELO"]), (50, 50))
        rect = pygame.Rect(50, 120, LARGURA_TELA - 100, 200); desenhar_texto_multilinha(surface, f'"{self.evento_atual.descricao}"', rect, FONTES["DIALOGO"], CORES["BRANCO"])
        for b in self.botoes_evento: b.desenhar(surface)
        self.botao_sair.desenhar(surface)

    def desenhar_tela_dialogo(self, surface):
        surface.fill(CORES["CINZA"]); surface.blit(FONTES["TITULO"].render(f"Conversando com: {self.funcionario_em_dialogo.nome}", True, CORES["AMARELO"]), (50, 50))
        rect = pygame.Rect(50, 120, LARGURA_TELA - 100, 200); desenhar_texto_multilinha(surface, f'"{self.no_dialogo_atual.frase_abertura}"', rect, FONTES["DIALOGO"], CORES["BRANCO"])
        for b in self.botoes_dialogo: b.desenhar(surface)
        self.botao_sair.desenhar(surface)

    def desenhar_hud_jogo(self, surface):
        surface.fill(CORES["PRETO"])
        if self.lider_escolhido:
            pa_surf = FONTES["TITULO"].render(f"Pontos de Ação: {self.lider_escolhido.pontos_acao} / {self.lider_escolhido.max_pontos_acao}", True, CORES["AMARELO"]); surface.blit(pa_surf, (LARGURA_TELA/2 - pa_surf.get_width()/2, 30))
        surface.blit(FONTES["TITULO"].render(f"Dia: {self.projeto.get_dia_semana()}", True, CORES["AZUL"]), (50, 30))
        surface.blit(FONTES["TITULO"].render(f"Pontos: {self.projeto.pontos_de_projeto}/{self.projeto.meta_pontos}", True, CORES["AZUL"]), (LARGURA_TELA-450, 30))
        if self.lider_escolhido: surface.blit(FONTES["TEXTO"].render(f"Líder: {self.lider_escolhido.nome}", True, CORES["BRANCO"]), (50, 80))
        for i, f in enumerate(self.equipe):
            y = 120 + i*120
            surface.blit(FONTES["TITULO"].render(f"{f.nome} ({f.geracao})", True, CORES["BRANCO"]), (50, y))
            surface.blit(FONTES["TEXTO"].render(f"Respeito:{f.respeito} | Det:{f.determinacao}", True, CORES["VERDE"]), (50, y+40))
            surface.blit(FONTES["TEXTO"].render(f"Estresse:{f.estresse} | Comod.:{f.comodidade}", True, CORES["VERDE"]), (50, y+70))
        if self.lider_escolhido:
            tem_pa = self.lider_escolhido.pontos_acao > 0
            for nome, botao in self.botoes_conversar.items(): botao.ativo = tem_pa and (nome not in self.funcionarios_conversados_hoje); botao.desenhar(surface)
            if self.botao_habilidade: self.botao_habilidade.ativo = self.lider_escolhido.pontos_acao >= self.lider_escolhido.habilidade_custo; self.botao_habilidade.desenhar(surface)
        self.botao_finalizar_dia.desenhar(surface)
        self.botao_sair.desenhar(surface)
        if self.feedback_timer > 0:
            fb_surf = FONTES["TEXTO"].render(self.feedback_texto, True, CORES["AMARELO"]); surface.blit(fb_surf, (LARGURA_TELA/2 - fb_surf.get_width()/2, ALTURA_TELA-150)); self.feedback_timer -= 1
    
    def desenhar_tela_relatorio(self, surface):
        surface.fill(CORES["PRETO"])
        if self.feedback_final_gerado is None: self.feedback_final_gerado = self.gerar_texto_analise()
        titulo_surf = FONTES["TITULO"].render("Relatório Final do Projeto", True, CORES["BRANCO"]); surface.blit(titulo_surf, (LARGURA_TELA/2 - titulo_surf.get_width()/2, 20))
        if self.feedback_final_gerado:
            subtitulo_surf = FONTES["TEXTO"].render(self.feedback_final_gerado.get('titulo', ''), True, CORES["AMARELO"]); surface.blit(subtitulo_surf, (LARGURA_TELA/2 - subtitulo_surf.get_width()/2, 70))
        y_texto = 120
        if self.feedback_final_gerado:
            textos = ["analise_lideranca", "impacto_equipa", "feedback_futuro", "analise_eficacia"]; titulos = ["Análise de Liderança:", "Impacto na Equipa:", "Feedback para o Futuro:", "Análise de Eficácia:"]
            for i, key in enumerate(textos):
                titulo_seccao = FONTES["BOTAO"].render(titulos[i], True, CORES["AZUL"]); surface.blit(titulo_seccao, (50, y_texto)); y_texto += 25
                rect_texto = pygame.Rect(50, y_texto, LARGURA_TELA/2 - 100, 100); desenhar_texto_multilinha(surface, self.feedback_final_gerado.get(key, ''), rect_texto, FONTES["BOTAO"], CORES["BRANCO"]); y_texto += 110
        y_direita = 120
        pontos_surf = FONTES["TEXTO"].render(f"Pontuação Final: {self.projeto.pontos_de_projeto} / {self.projeto.meta_pontos}", True, CORES["BRANCO"]); surface.blit(pontos_surf, (LARGURA_TELA - 450, y_direita)); y_direita += 40
        legendas = [("R", CORES["GRAFICO_RESPEITO"]), ("D", CORES["GRAFICO_DETERMINACAO"]), ("E", CORES["GRAFICO_ESTRESSE"]), ("C", CORES["GRAFICO_COMODIDADE"])]
        for i, (t, c) in enumerate(legendas):
            pygame.draw.rect(surface, c, (LARGURA_TELA/2+50+i*100, y_direita, 15, 15)); ls = FONTES["BOTAO"].render(t, True, CORES["BRANCO"]); surface.blit(ls, (LARGURA_TELA/2+70+i*100, y_direita-2))
        y_direita += 40
        for i, f in enumerate(self.equipe):
            grafico_rect = pygame.Rect(LARGURA_TELA/2+50, y_direita+i*100, LARGURA_TELA/2-100, 80); pygame.draw.rect(surface, CORES["CINZA"], grafico_rect, 1)
            nome_surf = FONTES["BOTAO"].render(f.nome, True, CORES["BRANCO"]); surface.blit(nome_surf, (grafico_rect.left+5, grafico_rect.top-20))
            if not f.historico_status: continue
            dias = [h['dia'] for h in f.historico_status]; num_dias = len(dias)-1 if len(dias)>1 else 1
            pontos_x = [grafico_rect.left+10+(d-1)*((grafico_rect.width-20)/num_dias) for d in dias]
            for status, cor in [("respeito", CORES["GRAFICO_RESPEITO"]),("determinacao", CORES["GRAFICO_DETERMINACAO"]),("estresse", CORES["GRAFICO_ESTRESSE"]),("comodidade", CORES["GRAFICO_COMODIDADE"])]:
                pontos_y = [grafico_rect.bottom-5-(h[status]/10)*(grafico_rect.height-10) for h in f.historico_status]
                if len(pontos_x) > 1: pygame.draw.lines(surface, cor, False, list(zip(pontos_x, pontos_y)), 2)
        self.botao_sair.desenhar(surface)

    def terminar_jogo(self, resultado):
        self.resultado_final = resultado
        self.estado_jogo = "TELA_RELATORIO_FINAL"

    def gerar_texto_analise(self):
        if not self.lider_escolhido or not self.banco_feedbacks: return None
        contadores = self.lider_escolhido.contadores
        total_apoios = contadores['apoio_eficaz'] + contadores['apoio_ineficaz']
        total_pressoes = contadores['pressao_eficaz'] + contadores['pressao_ineficaz']
        total_acoes = total_apoios + total_pressoes
        estilo = "Equilibrado"
        if total_acoes > 0:
            if (total_pressoes / total_acoes) >= 0.6: estilo = "Focado em Resultados"
            elif (total_apoios / total_acoes) >= 0.6: estilo = "Focado na Equipa"
        feedback_data = self.banco_feedbacks.get(self.resultado_final, {}).get(estilo, {})
        
        total_eficazes = contadores['apoio_eficaz'] + contadores['pressao_eficaz']
        taxa_eficacia = (total_eficazes / total_acoes) * 100 if total_acoes > 0 else 0
        
        texto_eficacia = f"A sua taxa de eficácia nas conversas foi de {taxa_eficacia:.0f}%. "
        if taxa_eficacia >= 75: texto_eficacia += "Você demonstrou uma excelente leitura da equipe."
        elif taxa_eficacia >= 50: texto_eficacia += "Você foi eficaz na maioria das vezes, mas algumas escolhas podem não ter tido o impacto desejado."
        else: texto_eficacia += "Muitas das suas intervenções não tiveram o efeito esperado."
        
        feedback_data['analise_eficacia'] = texto_eficacia
        return feedback_data

    def avancar_dia(self):
        self.estado_jogo = "JOGO_PRINCIPAL"
        print(f"\n--- Fim da {self.projeto.get_dia_semana()} ---")
        for f in self.equipe: f.guardar_status_do_dia(self.projeto.dia_atual)
        pontos_gerados = sum(max(0,f.determinacao-max(0,f.estresse-f.limiar_estresse))*1.5 for f in self.equipe)
        self.projeto.pontos_de_projeto += int(pontos_gerados); print(f"Pontos gerados: {int(pontos_gerados)}")
        if self.projeto.pontos_de_projeto >= self.projeto.meta_pontos: self.terminar_jogo("Sucesso"); return
        if self.lider_escolhido:
            pa_antigo = self.lider_escolhido.pontos_acao
            self.lider_escolhido.pontos_acao = min(self.lider_escolhido.max_pontos_acao, pa_antigo + 2)
            print(f"PA regenerados: {pa_antigo} -> {self.lider_escolhido.pontos_acao}")
        self.projeto.dia_atual += 1
        if self.projeto.dia_atual > 5: self.terminar_jogo("Fracasso"); return
        print(f"--- Iniciando a {self.projeto.get_dia_semana()} ---")
        self.funcionarios_conversados_hoje = []
        if self.banco_eventos:
            self.evento_atual = random.choice(self.banco_eventos)
            self.botoes_evento = [Botao(100, 350+i*90, LARGURA_TELA-200, 80, o.texto_resposta) for i, o in enumerate(self.evento_atual.opcoes)]
            self.estado_jogo = "TELA_EVENTO"

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