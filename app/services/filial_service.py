from typing import Optional


class FilialService:
    def __init__(self, repository):
        self.repository = repository
        # Cache para busca rápida por IP (segmento -> código_er)
        self.mapa_ip_filial = {} 
        # Lista limpa para select/telas/outros serviços
        self.filiais_limpas = [] 
        self.RADICAL_CNPJ = "8326142"

    async def sincronizar_rede(self):
        res = await self.repository.get_filiais_raw()
        
        if res.sucesso:
            novas_filiais = []
            novo_mapa_ip = {}

            for item in res.dados:
                tipo = item.get('TIPO')
                
                # 1. Filtro de Segurança: Verifica o CNPJ (Campo 'CN')
                cnpj_bruto = str(item.get('CN', ''))
                if self.RADICAL_CNPJ not in cnpj_bruto:
                    continue

                # 2. Filtro de Ativo: Só considera filiais ativas (Campo 'ATIVO' == 1)
                if item.get('ATIVO') !=  1:
                    continue

                print("Codigo",item.get('CODIGO'), "Tipo", tipo, "Nome", item.get('NOME'))
                # 3. Filtro de Tipo: Só Loja (L) ou CD (C)
                if tipo not in ['L', 'C']:
                    continue

                cod_puro = str(item.get('CODIGO'))
                nome = item.get('NOME', 'Sem Nome').strip()

                # 4. Regra de negócio para o código filtrado (o que você usa no IP)
                if tipo == 'L':
                    filtrado = cod_puro[:-1]
                elif tipo == 'C':
                    filtrado = cod_puro[1:-1]

                dados_filial = {
                    "codigo_original": int(cod_puro),
                    "codigo_curto": filtrado,
                    "nome": nome,
                    "tipo": "Loja" if tipo == 'L' else "CD"
                }

                novas_filiais.append(dados_filial)
                
                # 5. Alimenta o mapa de busca por segmento de IP
                # Ex: se o filtrado for '17', o IP 10.17.x.x cai aqui
                novo_mapa_ip[filtrado] = int(cod_puro)

            # Swap do cache (atomicidade)
            self.filiais_limpas = novas_filiais
            self.mapa_ip_filial = novo_mapa_ip
            return True
        return False

    def obter_cod_empresa_por_ip(self, ip_cliente: str):
        try:
            segmento = ip_cliente.split('.')[1]
            return self.mapa_ip_filial.get(segmento)
        except:
            return None
        
    def encontra_filial_por_ip(self, ip_cliente: str) -> Optional[int]:
        """
        Recebe: '10.17.30.41'
        Processa: Pega o '17'
        Retorna: 175 (COD da loja)
        """
        if not ip_cliente:
            return None

        try:
            partes = ip_cliente.split('.')
            if len(partes) < 2:
                return None
                
            segmento = partes[1]  # Ex: '17'
            
            # Busca no dicionário pré-carregado (segmento -> código_original)
            codigo = self.mapa_ip_filial.get(segmento)
            
            print(f"[DEBUG] IP: {ip_cliente} -> Segmento: {segmento} -> Filial: {codigo}")
            return codigo
        except Exception as e:
            print(f"[ERRO] Falha ao traduzir IP {ip_cliente}: {e}")
            return None
            

    