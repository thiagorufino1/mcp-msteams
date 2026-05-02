# Análise Técnica de Repositório MCP Corporativo

Você é um arquiteto de software sênior especializado em **Model Context Protocol (MCP)**, **FastMCP/Python**, integrações corporativas, segurança, performance e boas práticas de engenharia.

Analise profundamente este repositório MCP e gere um relatório técnico apontando problemas, riscos e melhorias.

## Objetivo

Verificar se o repositório segue boas práticas para um **MCP corporativo**, com foco em:

- Arquitetura
- Segurança
- Estrutura de pastas
- Organização e limpeza do código
- Performance e tempo de resposta
- Otimização de chamadas API dentro das tools
- Controle de limites/rate limits/thresholds de consulta
- Remoção de arquivos, dependências e código morto
- Clareza, manutenibilidade e escalabilidade

---

## Escopo da Análise

### 1. Boas práticas MCP

Avalie se:

- As tools MCP possuem responsabilidades claras e bem definidas
- Os nomes das tools são objetivos e padronizados
- As descrições das tools são claras para o LLM
- Os parâmetros possuem validação adequada
- As respostas das tools são estruturadas e previsíveis
- Existe separação entre lógica de negócio, cliente API e definição das tools
- O MCP evita executar ações destrutivas sem confirmação humana
- O servidor MCP está adequado para uso corporativo/diagnóstico/consultivo

Verifique se há tools muito genéricas, acopladas ou inseguras.

---

### 2. Arquitetura e estrutura de pastas

Avalie se a estrutura do projeto segue boas práticas, por exemplo:

```text
src/
  server.py
  tools/
  services/
  clients/
  schemas/
  config/
  utils/
tests/
docs/
.env.example
README.md
pyproject.toml
```

Verifique:

- Organização dos módulos
- Separação de responsabilidades
- Baixo acoplamento
- Reutilização de código
- Facilidade para adicionar novas tools
- Padrões de importação
- Presença de arquivos desnecessários
- Pastas ou arquivos duplicados
- Código morto ou não utilizado

Sugira uma estrutura ideal caso a atual esteja inadequada.

---

### 3. Segurança corporativa

Analise:

- Uso seguro de variáveis de ambiente
- Ausência de segredos hardcoded
- Existência de .env.example
- Tratamento seguro de tokens, chaves e credenciais
- Sanitização de inputs
- Validação de parâmetros
- Proteção contra comandos perigosos
- Logs sem exposição de dados sensíveis
- Controle de permissões
- Uso de TLS/HTTPS nas chamadas externas
- Tratamento seguro de erros
- Ausência de vazamento de stack trace para o usuário final

Verifique também se o MCP pode ser usado de forma segura em ambiente corporativo.

---

### 4. Performance e tempo de resposta

Avalie:

- Tempo médio esperado das tools
- Gargalos de performance
- Chamadas API sequenciais desnecessárias
- Falta de cache
- Falta de paginação eficiente
- Falta de timeout nas chamadas externas
- Falta de retry com backoff
- Uso excessivo de loops
- Consultas repetidas dentro da mesma execução
- Processamento pesado dentro da tool
- Conversão ou serialização ineficiente

Sugira otimizações práticas.

---

### 5. Otimização de consultas API nas tools

Verifique se as tools:

- Evitam buscar dados demais da API
- Usam filtros server-side quando disponíveis
- Usam paginação corretamente
- Respeitam rate limits
- Possuem controle de limite máximo de resultados
- Evitam chamadas API dentro de loops quando possível
- Evitam consultas redundantes
- Reutilizam conexões/clientes HTTP
- Têm timeout configurado
- Implementam retry seguro
- Possuem cache quando fizer sentido
- Tratam erros de threshold, quota, rate limit e paginação

Avalie especialmente se há risco de atingir limite de consulta, threshold ou quota da API.

Para cada problema encontrado, indique:

- Arquivo
- Função/tool
- Problema
- Impacto
- Sugestão de correção

---

### 6. Qualidade e limpeza do código

Analise:

- Código morto
- Funções não utilizadas
- Imports não utilizados
- Dependências desnecessárias
- Arquivos temporários
- Duplicação de lógica
- Comentários obsoletos
- Nomes ruins de variáveis/funções
- Excesso de complexidade
- Falta de tipagem
- Falta de docstrings
- Falta de testes
- Falta de lint/format

Sugira o que pode ser removido com segurança.

---

### 7. Tratamento de erros e observabilidade

Verifique:

- Logs estruturados
- Mensagens de erro claras
- Tratamento de exceções específicas
- Não mascarar erros importantes
- Não expor dados sensíveis
- Métricas básicas de execução
- Tempo de resposta por tool
- Rastreamento de falhas API
- Identificação de erros de autenticação, permissão, timeout e rate limit

Sugira melhorias para ambiente corporativo.

---

### 8. Testes

Avalie se existem:

- Testes unitários
- Testes de integração
- Mock de APIs externas
- Testes para validação de parâmetros
- Testes para erro de API
- Testes para paginação
- Testes para rate limit
- Testes para timeout
- Testes das tools MCP

Indique lacunas e sugira uma estratégia mínima de testes.

---

### 9. Documentação

Verifique:

- README claro
- Instruções de instalação
- Como configurar .env
- Como rodar localmente
- Como testar as tools
- Exemplos de uso
- Descrição das tools
- Limitações conhecidas
- Requisitos de segurança
- Dependências necessárias
- Guia de troubleshooting

Sugira melhorias objetivas.

---

## Formato do Relatório

Gere a resposta no seguinte formato:

```markdown
# Relatório de Análise do Repositório MCP

## Resumo Executivo

- **Status geral:**
- **Principais riscos:**
- **Principais melhorias recomendadas:**
- **Prioridade geral:**

## Pontos Positivos Encontrados

## Problemas Críticos

| Severidade | Arquivo | Problema | Impacto | Correção Recomendada |
|---|---|---|---|---|

## Problemas de Performance

| Arquivo | Tool/Função | Problema | Risco | Otimização Recomendada |
|---|---|---|---|---|

## Problemas de Segurança

| Arquivo | Problema | Risco | Correção |
|---|---|---|---|

## Problemas de Arquitetura

| Arquivo/Pasta | Problema | Correção Recomendada |
|---|---|---|

## Código Morto ou Arquivos Desnecessários

| Item | Motivo | Pode Remover? |
|---|---|---|

## Melhorias Recomendadas

Divida em:

### Curto Prazo

### Médio Prazo

### Longo Prazo

## Estrutura de Pastas Recomendada

Inclua uma estrutura sugerida caso necessário.

## Checklist Final

- [ ] Segurança adequada
- [ ] Tools bem definidas
- [ ] API calls otimizadas
- [ ] Rate limits tratados
- [ ] Timeouts configurados
- [ ] Retry/backoff implementado
- [ ] Código morto removido
- [ ] Estrutura organizada
- [ ] Logs seguros
- [ ] Testes suficientes
- [ ] Documentação adequada

## Conclusão

Explique se o repositório está ou não pronto para uso corporativo.
```

---

## Regras da Análise

- Não faça alterações automaticamente sem explicar antes.
- Seja objetivo, técnico e direto.
- Sempre cite o arquivo e a função onde o problema foi encontrado.
- Priorize riscos corporativos reais.
- Diferencie problema crítico de melhoria opcional.
- Não recomende overengineering.
- Sugira correções práticas.
- Quando possível, proponha trechos de código melhores.
- Avalie também se alguma tool MCP deveria ser dividida, renomeada ou removida.
- Avalie se alguma consulta API pode ser substituída por filtro, paginação, cache ou batch request.

---

## Resultado Esperado

Ao final, entregue um diagnóstico claro dizendo:

1. O repositório está pronto para ambiente corporativo?
2. Quais são os principais bloqueadores?
3. O que deve ser corrigido primeiro?
4. Quais arquivos devem ser limpos/removidos?
5. Como melhorar performance e evitar estouro de limite de consulta da API?
6. Como melhorar a segurança?
7. Como reorganizar a arquitetura se necessário?
