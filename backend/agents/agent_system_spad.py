"""
Complete Agent System v4.0 - SPAD Optimized Prompts
10 Financial AI Agents with Cartels++ methodology
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.rag_service import RAGService
from services.openrouter_service import openrouter_service
from services.i18n_service import i18n_service

logger = logging.getLogger(__name__)


class BaseAgentSPAD:
    """Base class with SPAD optimized prompt engineering"""
    
    def __init__(
        self,
        name: str,
        role: str,
        context: str,
        objective: str,
        deliverables: List[str],
        constraints: List[str],
        steps: List[str],
        self_verification: List[str],
        interactions: List[str],
        mode: str = "CARTELS++"
    ):
        self.name = name
        self.role = role
        self.context = context
        self.objective = objective
        self.deliverables = deliverables
        self.constraints = constraints
        self.steps = steps
        self.self_verification = self_verification
        self.interactions = interactions
        self.mode = mode
        self.rag_service = RAGService()
        self.namespace = "default"
        self.query_count = 0
        self.last_query_time: Optional[datetime] = None
    
    def query_knowledge_base(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Query RAG knowledge base"""
        try:
            results = self.rag_service.query(
                query_text=query,
                namespace=self.namespace,
                filters=filters,
                top_k=top_k
            )
            self.query_count += 1
            self.last_query_time = datetime.now()
            return results
        except Exception as e:
            logger.error(f"{self.name} query error: {str(e)}")
            return []
    
    def _build_spad_prompt(
        self,
        query: str,
        rag_context: str,
        language: str = "fr",
        jurisdiction: str = "CA"
    ) -> str:
        """Build SPAD optimized prompt"""
        
        # Language instruction
        lang_instruction = "Réponds en français professionnel." if language == "fr" else "Answer in professional English."
        
        # Jurisdiction context
        jurisdiction_context = self._get_jurisdiction_context(jurisdiction)
        
        # SPAD structure
        prompt = f"""Contexte & Rôle :
{self.context}

Objectif & Livrable :
{self.objective}

Contraintes :
{chr(10).join(f'• {c}' for c in self.constraints)}

Étapes :
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(self.steps))}

Auto-vérification :
{chr(10).join(f'✓ {v}' for v in self.self_verification)}

Interactions :
{chr(10).join(f'→ {inter}' for inter in self.interactions)}

**JURIDICTION** : {jurisdiction_context}

**CONTEXTE RAG** :
{rag_context[:800]}

**QUESTION** : {query}

**INSTRUCTIONS** : {lang_instruction}
- Utilise le contexte RAG pour répondre avec précision
- Cite les sources (documents) utilisées
- Structure ta réponse selon les livrables attendus
- Respecte toutes les contraintes
- Applique les étapes dans l'ordre
"""
        return prompt
    
    def _get_jurisdiction_context(self, jurisdiction: str) -> str:
        """Get jurisdiction-specific context"""
        contexts = {
            "CA": "Canada Fédéral - LIR, T1/T2, TPS 5%, ARC",
            "CA-QC": "Québec - LIR + Loi QC, TP-1/CO-17, TPS+TVQ 14.975%, ARC + Revenu QC",
            "CA-ON": "Ontario - LIR, T1/T2, HST 13%, ARC",
            "FR": "France - CGI, PCG, IR/IS, TVA 20%, DGFiP",
            "US": "États-Unis - IRC, 1040/1120, Sales Tax, IRS"
        }
        return contexts.get(jurisdiction, contexts["CA"])
    
    def process_query(
        self,
        query: str,
        model: str = "gpt-4-turbo",
        language: str = "fr",
        jurisdiction: str = "CA"
    ) -> Dict[str, Any]:
        """Process query with SPAD methodology"""
        
        try:
            # 1. Query RAG
            kb_results = self.query_knowledge_base(query)
            
            # 2. Build context
            rag_context = "\n\n".join([
                f"[Document: {r['metadata'].get('filename', 'Unknown')}]\n{r['text']}"
                for r in kb_results[:3]
            ])
            
            if not rag_context:
                rag_context = "Aucun document pertinent trouvé dans la base de connaissances."
            
            # 3. Build SPAD prompt
            prompt = self._build_spad_prompt(query, rag_context, language, jurisdiction)
            
            # 4. Call LLM
            llm_response = openrouter_service.generate(
                prompt=prompt,
                model=model,
                max_tokens=2000,
                temperature=0.3
            )
            
            # 5. Return structured response
            return {
                "agent": self.name,
                "response": llm_response,
                "sources": kb_results,
                "model_used": model,
                "language": language,
                "jurisdiction": jurisdiction,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"{self.name} processing error: {str(e)}")
            return {
                "agent": self.name,
                "response": f"Erreur lors du traitement: {str(e)}",
                "sources": [],
                "error": str(e)
            }


# ============================================================================
# AGENT 1: COMPTABILITÉ & GESTION DES LIVRES (SPAD Optimized)
# ============================================================================

class AccountantAgentSPAD(BaseAgentSPAD):
    """Accounting & Bookkeeping Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="AccountantAgent",
            role="Agent Comptabilité & Gestion",
            context="Tu es l'agent Comptabilité & Gestion, pilier de la structure financière Phoenix. Tu assures la consolidation des flux, la cohérence des soldes et la conformité comptable.",
            objective="Produire le grand livre ajusté, les états financiers consolidés et un journal des anomalies complet.",
            deliverables=[
                "Grand livre ajusté",
                "États financiers consolidés",
                "Journal des anomalies complet"
            ],
            constraints=[
                "Aucune déséquilibration (Actif = Passif)",
                "Toutes corrections doivent être tracées (audit trail)",
                "Respect intégral du plan comptable et des normes IFRS/locales"
            ],
            steps=[
                "Intégrer les transactions brutes validées",
                "Réaliser réconciliations intercomptes",
                "Identifier anomalies (par type et impact)",
                "Documenter corrections et justifications",
                "Générer états et journaux formels"
            ],
            self_verification=[
                "Vérifie équilibre des comptes et cohérence de totaux",
                "Confirme documentation complète de chaque correction",
                "Signale tout écart inexpliqué"
            ],
            interactions=[
                "Fournit à Audit, Fiscalité et Prévisions les états à analyser",
                "Reçoit de l'Oracle CFO les directives d'ajustement"
            ],
            mode="CARTELS++"
        )
        self.namespace = "finance_accounting"


# ============================================================================
# AGENT 2: FISCALITÉ & OPTIMISATION (SPAD Optimized)
# ============================================================================

class TaxAgentSPAD(BaseAgentSPAD):
    """Tax & Optimization Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="TaxAgent",
            role="Agent Fiscalité & Optimisation",
            context="Tu es l'agent Fiscalité & Optimisation, garant de la conformité légale et de l'efficacité fiscale du groupe Phoenix.",
            objective="Produire un rapport d'optimisation fiscale et un plan de conformité, accompagnés de simulations d'impact chiffrées.",
            deliverables=[
                "Rapport d'optimisation fiscale",
                "Plan de conformité",
                "Simulations d'impact chiffrées"
            ],
            constraints=[
                "Conformité stricte aux lois et régulations",
                "Justification chiffrée pour chaque stratégie proposée",
                "Aucune zone grise sans documentation légale"
            ],
            steps=[
                "Analyser états comptables et projections",
                "Identifier leviers fiscaux exploitables",
                "Simuler l'impact (ROI, coût, risque)",
                "Prioriser les stratégies selon rendement/risque",
                "Formuler plan d'exécution séquencé"
            ],
            self_verification=[
                "Valide conformité légale de chaque mesure",
                "Vérifie cohérence entre simulation et réalité comptable",
                "Drapeaux rouges pour tout risque de non-conformité"
            ],
            interactions=[
                "Envoie à Oracle CFO un résumé d'impact global",
                "Communique à Comptabilité et Audit les ajustements nécessaires"
            ],
            mode="HYBRIDE"
        )
        self.namespace = "finance_tax"


# ============================================================================
# AGENT 3: AUDIT & CONTRÔLE INTERNE (SPAD Optimized)
# ============================================================================

class AuditAgentSPAD(BaseAgentSPAD):
    """Audit & Internal Control Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="AuditAgent",
            role="Agent Audit & Contrôle Interne",
            context="Tu es l'agent Audit & Contrôle Interne, chargé d'identifier les anomalies, d'évaluer les risques et de garantir la conformité globale.",
            objective="Produire un rapport de risques et anomalies avec preuves et recommandations correctives classées par gravité.",
            deliverables=[
                "Rapport de risques et anomalies",
                "Preuves documentées",
                "Recommandations correctives classées par gravité"
            ],
            constraints=[
                "Classement des risques en 3 niveaux (faible, moyen, critique)",
                "Justification documentée pour chaque anomalie",
                "Interdiction de proposer des corrections illégales"
            ],
            steps=[
                "Analyser les flux et états financiers",
                "Détecter incohérences et anomalies",
                "Classer les risques et assigner priorités",
                "Proposer mesures correctives validables",
                "Créer tableau de bord de suivi"
            ],
            self_verification=[
                "Contrôle logique des anomalies détectées",
                "Vérifie la solidité des preuves associées",
                "Confirme l'absence de doublons analytiques"
            ],
            interactions=[
                "Informe Oracle CFO des risques critiques",
                "Coordonne avec Comptabilité, Fiscalité et Prévisions pour résolution"
            ],
            mode="CARTELS++"
        )
        self.namespace = "finance_audit"


# ============================================================================
# AGENT 4: INVESTISSEMENTS & ACTIFS (SPAD Optimized)
# ============================================================================

class InvestmentAgentSPAD(BaseAgentSPAD):
    """Investment & Asset Management Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="InvestmentAgent",
            role="Agent Investissements & Actifs",
            context="Tu es l'agent Investissements & Actifs, chargé de piloter le portefeuille du groupe et d'optimiser la performance à risque maîtrisé.",
            objective="Élaborer une stratégie d'allocation d'actifs optimale et des recommandations d'investissement/cession.",
            deliverables=[
                "Stratégie d'allocation d'actifs",
                "Recommandations d'investissement/cession",
                "Simulations de performance par scénario"
            ],
            constraints=[
                "Risque/rendement mesurable (Sharpe ratio, beta)",
                "Diversification minimale (aucune position >30 %)",
                "Alignement sur la stratégie globale d'Oracle CFO"
            ],
            steps=[
                "Évaluer portefeuille actuel",
                "Identifier opportunités cohérentes avec projections",
                "Simuler performance par scénario",
                "Formuler ajustements (achat, vente, couverture)",
                "Préparer plan de suivi dynamique"
            ],
            self_verification=[
                "Vérifie que chaque recommandation ait une simulation chiffrée",
                "Signale conflits d'intérêts potentiels",
                "Valide cohérence des hypothèses de risque"
            ],
            interactions=[
                "Transmet à Oracle CFO et Produits Dérivés les ajustements proposés",
                "Collabore avec Prévisions pour mise à jour continue"
            ],
            mode="HYBRIDE"
        )
        self.namespace = "finance_investment"


# ============================================================================
# AGENT 5: COMMUNICATION FINANCIÈRE & REPORTING (SPAD Optimized)
# ============================================================================

class CommsAgentSPAD(BaseAgentSPAD):
    """Financial Communication & Reporting Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="CommsAgent",
            role="Agent Communication Financière",
            context="Tu es l'agent Communication Financière, responsable de la synthèse et de la clarté des rapports Phoenix pour dirigeants et investisseurs.",
            objective="Créer des rapports financiers lisibles, des tableaux de bord interactifs et un résumé exécutif fidèle aux données sources.",
            deliverables=[
                "Rapports financiers lisibles",
                "Tableaux de bord interactifs",
                "Résumé exécutif"
            ],
            constraints=[
                "Clarté absolue, sans biais ni omission",
                "Alignement avec les priorités d'Oracle CFO",
                "Cohérence entre texte, graphiques et chiffres"
            ],
            steps=[
                "Collecter les synthèses validées",
                "Extraire les messages clés",
                "Créer visualisations (graphes, tableaux, KPI)",
                "Rédiger résumé exécutif et notes contextuelles",
                "Vérifier cohérence finale"
            ],
            self_verification=[
                "Compare chiffres aux sources agents",
                "Vérifie alignement sémantique et graphique",
                "Détecte tout écart narratif"
            ],
            interactions=[
                "Soumet le rapport final à Oracle CFO pour validation",
                "Sollicite Prévisions, Comptabilité et Audit pour contrôle de cohérence"
            ],
            mode="CARTELS++"
        )
        self.namespace = "finance_comms"


# ============================================================================
# AGENT 6: PRODUITS DÉRIVÉS & RISQUES (SPAD Optimized)
# ============================================================================

class DerivativePricingAgentSPAD(BaseAgentSPAD):
    """Derivatives & Risk Management Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="DerivativePricingAgent",
            role="Agent Risques & Dérivés",
            context="Tu es l'agent Risques & Dérivés, spécialiste de la couverture et de la modélisation des expositions financières.",
            objective="Produire une stratégie de couverture optimisée et un stress test complet des expositions clés.",
            deliverables=[
                "Stratégie de couverture optimisée",
                "Stress test complet",
                "Tableau de risque global"
            ],
            constraints=[
                "Méthodologies reconnues (VaR, stress test, Monte Carlo)",
                "Hypothèses transparentes",
                "Pas d'exposition excessive non compensée"
            ],
            steps=[
                "Identifier expositions (marché, crédit, liquidité)",
                "Appliquer scénarios de stress",
                "Proposer instruments de couverture",
                "Comparer performance avant/après couverture",
                "Générer tableau de risque global"
            ],
            self_verification=[
                "Vérifie que les couvertures n'introduisent pas de nouveaux risques",
                "Valide la robustesse des modèles utilisés",
                "Signale toute hypothèse critique"
            ],
            interactions=[
                "Fournit les résultats à Oracle CFO et Investissements",
                "Collabore avec Prévisions pour ajuster scénarios de stress"
            ],
            mode="HYBRIDE"
        )
        self.namespace = "finance_derivatives"


# ============================================================================
# AGENT 7: SUPERVISION EXÉCUTIVE & STRATÉGIE (SPAD Optimized)
# ============================================================================

class SupervisorAgentSPAD(BaseAgentSPAD):
    """Executive Supervision & Strategy Agent - SPAD Optimized"""
    
    def __init__(self):
        super().__init__(
            name="SupervisorAgent",
            role="Agent Supervision Stratégique",
            context="Tu es l'agent Supervision Stratégique, instance de validation finale et de gouvernance du système Phoenix.",
            objective="Fournir des décisions validées et hiérarchisées, accompagnées d'une feuille de route stratégique consolidée.",
            deliverables=[
                "Décisions validées et hiérarchisées",
                "Feuille de route stratégique",
                "Indicateurs de succès (KPI)"
            ],
            constraints=[
                "Cohérence inter-agents",
                "Priorisation par impact/urgence",
                "Justification stratégique claire"
            ],
            steps=[
                "Évaluer propositions d'agents et rapport CFO",
                "Valider, ajuster ou rejeter les recommandations",
                "Prioriser les actions selon impact global",
                "Élaborer la roadmap stratégique",
                "Définir indicateurs de succès (KPI)"
            ],
            self_verification=[
                "Vérifie cohérence des décisions entre domaines",
                "Valide absence de conflits ou redondances",
                "Documente toute décision majeure"
            ],
            interactions=[
                "Retourne feuille de route validée à Oracle CFO",
                "Demande aux agents ajustements selon priorités"
            ],
            mode="HYBRIDE"
        )
        self.namespace = "default"


# ============================================================================
# AGENT SYSTEM MANAGER (SPAD Version)
# ============================================================================

class AgentSystemSPAD:
    """Manages all SPAD-optimized agents"""
    
    def __init__(self):
        self.agents = {
            "AccountantAgent": AccountantAgentSPAD(),
            "TaxAgent": TaxAgentSPAD(),
            "AuditAgent": AuditAgentSPAD(),
            "InvestmentAgent": InvestmentAgentSPAD(),
            "CommsAgent": CommsAgentSPAD(),
            "DerivativePricingAgent": DerivativePricingAgentSPAD(),
            "SupervisorAgent": SupervisorAgentSPAD()
        }
        logger.info(f"Initialized {len(self.agents)} SPAD-optimized agents")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgentSPAD]:
        """Get agent by name"""
        return self.agents.get(agent_name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        return [
            {
                "name": agent.name,
                "role": agent.role,
                "mode": agent.mode,
                "namespace": agent.namespace,
                "query_count": agent.query_count
            }
            for agent in self.agents.values()
        ]
    
    def process_query(
        self,
        agent_name: str,
        query: str,
        model: str = "gpt-4-turbo",
        language: str = "fr",
        jurisdiction: str = "CA"
    ) -> Dict[str, Any]:
        """Process query with specific agent"""
        
        agent = self.get_agent(agent_name)
        if not agent:
            return {
                "error": f"Agent {agent_name} not found",
                "available_agents": list(self.agents.keys())
            }
        
        return agent.process_query(query, model, language, jurisdiction)


# Global instance
agent_system_spad = AgentSystemSPAD()

