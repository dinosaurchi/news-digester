import type { ReportMessage, ReportThread, FeedbackVote } from '@/types';
import { delay, randomBetween } from './helpers';
import { MOCK_THREADS } from './reports';

export const MOCK_MESSAGES: Record<string, ReportMessage[]> = {
  'th-1': [
    {
      id: 'm-1',
      threadId: 'th-1',
      role: 'system',
      content: `# Daily Intelligence Report: TechCorp Strategy

**Date:** March 20, 2024 | **Period:** March 19–20, 2024
**Workspace:** TechCorp Inc. | **Articles Scanned:** 156 | **Included:** 12

---

## Executive Summary

Today's intelligence landscape is dominated by the **EU AI Act implementation timeline** announcement and aggressive **edge computing expansion** by CloudGiant. Additionally, hybrid cloud adoption continues to surge among Fortune 500 companies, validating TechCorp's core market thesis.

---

## Key Developments

### 1. Regulatory: EU AI Act Implementation Timeline Published
**Source:** Reuters | **Score:** 94/100 | **Impact:** 🔴 High

The European Commission has published the detailed implementation timeline for the EU AI Act. Key milestones:

| Deadline | Requirement |
|----------|------------|
| Feb 2025 | Prohibited AI practices banned |
| Aug 2025 | General-purpose AI obligations |
| Aug 2026 | High-risk AI system requirements |

> **Action Required:** TechCorp should audit CloudStack Pro and AI-Flow Engine for compliance with high-risk AI system requirements. Legal and product teams should begin gap analysis immediately.

### 2. Competitive: CloudGiant Announces 10 New Edge Data Centers
**Source:** CloudGiant Press | **Score:** 87/100 | **Impact:** 🟡 Medium

CloudGiant has unveiled a $2.3 billion investment in 10 new European edge data center locations (London, Frankfurt, Paris, Amsterdam, Dublin, Stockholm, Zurich, Warsaw, Madrid, Milan) by Q4 2025.

> **Strategic Implication:** This directly challenges TechCorp's Edge-Connect Hub product. Consider accelerating Edge-Connect beta testing and preparing competitive positioning documents for enterprise customers evaluating edge solutions.

### 3. Market: Hybrid Cloud Adoption Surges 47% Among Fortune 500
**Source:** Cloud News Daily | **Score:** 90/100 | **Impact:** 🟢 Positive

A new industry survey shows 47% YoY growth in hybrid cloud adoption, with 78% citing AI workloads as the primary driver. Average annual cloud spend reached $4.2M per enterprise.

> **Opportunity:** Strong market tailwind for CloudStack Pro. Consider using this data in Q2 sales enablement materials.

### 4. Security: NIST Cybersecurity Framework 2.0 Released
**Source:** Wired | **Score:** 81/100 | **Impact:** 🟡 Medium

NIST has released Cybersecurity Framework 2.0 with enhanced focus on supply chain security and governance.

> **Action Required:** Product team should review implications for DataGuard Shield certification and compliance positioning.

---

## Recommended Actions

1. **Immediate:** Initiate EU AI Act compliance gap analysis for CloudStack Pro and AI-Flow Engine
2. **This Week:** Prepare competitive response strategy for CloudGiant edge expansion
3. **Q2 Planning:** Leverage hybrid cloud adoption data in sales enablement
4. **Ongoing:** Monitor NIST 2.0 adoption timeline for DataGuard roadmap`,
      createdAt: '2024-03-20T08:00:05Z',
      metadata: {
        sources: ['c-1', 'c-2', 'c-4', 'c-6'],
        reportId: 'rep-1',
        model: 'gpt-4-turbo',
        tokens: 2847,
      },
    },
    {
      id: 'm-2',
      threadId: 'th-1',
      role: 'user',
      content: 'Can you dig deeper into the CloudGiant edge expansion? I want to understand which of their new data center locations overlap with our existing Edge-Connect Hub customer base.',
      createdAt: '2024-03-20T09:30:00Z',
    },
    {
      id: 'm-3',
      threadId: 'th-1',
      role: 'agent',
      content: `Great question. Based on the announcement and our customer data analysis:

## CloudGiant Edge Expansion vs. Edge-Connect Hub Overlap

**Directly overlapping locations (High Priority):**
- **Frankfurt** — Our largest European Edge-Connect deployment (47 enterprise customers)
- **London** — Second-largest market (32 enterprise customers)
- **Amsterdam** — Growing market with 18 customers
- **Paris** — 15 customers, including 3 Fortune 500 accounts

**Adjacent competition (Medium Priority):**
- **Dublin** — 12 customers; CloudGiant presence will create pricing pressure
- **Zurich** — 8 customers, primarily financial services

**Limited direct overlap:**
- **Stockholm, Warsaw, Madrid, Milan** — Fewer than 5 Edge-Connect customers each

## Strategic Recommendation

The Frankfurt and London markets represent **79%** of our European Edge-Connect customer base that will face direct competition from CloudGiant. I recommend:

1. **Customer retention outreach** for the top 20 accounts in Frankfurt and London within the next 30 days
2. **Competitive positioning document** highlighting Edge-Connect advantages (lower latency, existing customer integrations)
3. **Pricing review** to ensure we remain competitive against CloudGiant's anticipated European pricing

Shall I prepare a more detailed competitive analysis for any specific market?`,
      createdAt: '2024-03-20T09:31:30Z',
      metadata: {
        sources: ['c-2'],
        model: 'gpt-4-turbo',
        tokens: 1923,
      },
    },
    {
      id: 'm-4',
      threadId: 'th-1',
      role: 'user',
      content: 'Yes, please prepare the Frankfurt competitive analysis. Also, can you include any information about their pricing model?',
      createdAt: '2024-03-20T10:15:00Z',
    },
    {
      id: 'm-5',
      threadId: 'th-1',
      role: 'agent',
      content: `## Frankfurt Market: Edge-Connect Hub vs. CloudGiant Edge

### Current State

**Edge-Connect Hub in Frankfurt:**
- 47 active enterprise customers
- Average contract value: $18,500/month
- 99.97% uptime SLA
- 12ms average latency to German enterprise customers

**CloudGiant's Frankfurt Plans:**
- New edge data center operational by Q2 2025
- Estimated capacity: 200+ enterprise customers
- Expected pricing: €12,000–€15,000/month (estimated based on their US pricing)

### Competitive Positioning

| Factor | Edge-Connect Hub | CloudGiant Edge |
|--------|-----------------|-----------------|
| Latency | 12ms avg | ~15-18ms est. |
| SLA | 99.97% | 99.95% (typical) |
| Integration | Native with CloudStack Pro | Proprietary stack |
| Support | Dedicated CSM | Tiered support |
| Pricing | $18,500/mo avg | €12,000-15,000/mo est. |

### Key Differentiators

1. **Integration depth** — Edge-Connect integrates natively with CloudStack Pro, giving existing customers a significant switching cost advantage
2. **Performance** — Our Frankfurt node has been optimized for 3 years; CloudGiant is starting from scratch
3. **Compliance** — We have existing GDPR and BSI certifications; CloudGiant will need to obtain these

### Recommended Actions

1. **Immediate:** Create a Frankfurt-specific competitive battle card for the sales team
2. **Within 2 weeks:** Schedule retention calls with the top 10 Frankfurt accounts
3. **This month:** Evaluate whether a loyalty discount program would reduce churn risk

> **Risk Assessment:** Medium-High. CloudGiant's pricing advantage (~20-30% lower) is the primary threat. However, switching costs and integration depth provide a strong defensive moat for existing customers.`,
      createdAt: '2024-03-20T10:17:00Z',
      metadata: {
        sources: ['c-2'],
        model: 'gpt-4-turbo',
        tokens: 2241,
      },
    },
  ],
  'th-2': [
    {
      id: 'm-10',
      threadId: 'th-2',
      role: 'system',
      content: `# Weekly Strategic Brief: TechCorp Strategy

**Period:** March 11–18, 2024 | **Articles Scanned:** 312 | **Included:** 24

---

## Executive Summary

This week saw three major themes: **Gartner's bullish GenAI enterprise predictions**, a **significant edge computing market forecast**, and the **Kubernetes 1.30 release** with GPU scheduling improvements. The competitive landscape remained active with SoftSystems launching a new enterprise AI platform.

---

## Top Stories

### 1. Gartner: 80% of Enterprises Will Use GenAI by 2026
**Source:** Gartner | **Score:** 77/100
Forecasts generative AI will be standard in 80% of enterprise software by 2026, with early adopters seeing significant productivity gains.

### 2. Edge Computing Market to Reach $61.4B by 2028
**Source:** MarketsandMarkets | **Score:** 72/100
CAGR of 25.3% driven by IoT proliferation, real-time processing needs, and 5G expansion.

### 3. Kubernetes 1.30: Advanced GPU Scheduling
**Source:** Kubernetes Blog | **Score:** 70/100
Dynamic GPU partitioning and multi-GPU pod scheduling improvements benefit AI/ML containerized workloads.

### 4. NovaTech Releases Open-Source AI Orchestration Tool
**Source:** NovaTech Blog | **Score:** 67/100
"NovaFlow" open-source tool under Apache 2.0 license with 2,000+ GitHub stars. Direct competitive threat to AI-Flow Engine.

### 5. EU Announces €2B Sovereign Cloud Investment
**Source:** EU Regulatory Digest | **Score:** 79/100
Three new cloud regions planned, with partnerships for European cloud providers.

---

## Week-over-Week Trends

| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Relevant articles | 24 | 18 | +33% |
| Avg. relevance score | 0.76 | 0.72 | +5.6% |
| Competitor mentions | 8 | 5 | +60% |
| Regulatory alerts | 2 | 1 | +100% |`,
      createdAt: '2024-03-18T08:00:05Z',
      metadata: {
        sources: ['c-8', 'c-10', 'c-11', 'c-13', 'c-14'],
        reportId: 'rep-2',
        model: 'gpt-4-turbo',
        tokens: 2156,
      },
    },
  ],
  'th-3': [
    {
      id: 'm-20',
      threadId: 'th-3',
      role: 'system',
      content: `# ⚠️ Competitive Alert: March 19, 2024

**Priority:** HIGH | **Workspace:** TechCorp Inc.

---

## Alert Summary

Three significant competitive developments require immediate attention:

---

## 1. DataNexus Acquires AI Security Startup SecureAI — $340M
**Source:** TechCrunch | **Score:** 85/100

DataNexus has acquired SecureAI, an AI-powered cybersecurity startup, for $340M. The acquisition will be integrated into DataNexus's enterprise security suite.

**Impact Assessment:**
- Directly strengthens DataNexus's position against TechCorp's DataGuard Shield
- SecureAI's threat detection capabilities will close a key gap in DataNexus's security portfolio
- Combined with the CloudGiant partnership (below), creates a formidable security + cloud offering

---

## 2. SoftSystems Launches Enterprise AI Platform
**Source:** SoftSystems Blog | **Score:** 82/100

SoftSystems International has launched an Enterprise AI Platform directly targeting CloudStack Pro and AI-Flow Engine markets. Starting at $15,000/month — significantly undercutting TechCorp's enterprise tier.

**Impact Assessment:**
- Pricing pressure on CloudStack Pro enterprise segment
- May appeal to mid-market customers evaluating alternatives
- Product maturity likely lower but improving rapidly

---

## 3. CloudGiant × DataNexus Strategic Partnership
**Source:** CloudGiant Press | **Score:** 88/100

CloudGiant and DataNexus have formed a strategic alliance to integrate cloud infrastructure and cybersecurity platforms.

**Impact Assessment:**
- Creates a combined cloud + security offering that directly competes with TechCorp's integrated portfolio
- Potential for joint go-to-market targeting TechCorp's shared customer base
- Represents the most significant competitive development this quarter

---

## Recommended Response

1. **Immediate:** Schedule competitive intelligence briefing for executive team
2. **Within 48 hours:** Prepare competitive battle cards for sales team
3. **This week:** Conduct customer satisfaction survey for top 50 accounts at risk
4. **Next sprint:** Evaluate pricing strategy adjustments for enterprise tier`,
      createdAt: '2024-03-19T14:00:05Z',
      metadata: {
        sources: ['c-5', 'c-9', 'c-12'],
        reportId: 'rep-3',
        model: 'gpt-4-turbo',
        tokens: 2456,
      },
    },
    {
      id: 'm-21',
      threadId: 'th-3',
      role: 'user',
      content: 'What do we know about SoftSystems\' new platform? Is it a credible threat or just vaporware?',
      createdAt: '2024-03-19T15:00:00Z',
    },
    {
      id: 'm-22',
      threadId: 'th-3',
      role: 'agent',
      content: `Based on the available intelligence, here's my assessment of the SoftSystems Enterprise AI Platform threat level:

## SoftSystems Enterprise AI Platform — Credibility Assessment

**Overall Threat Level:** 🟡 Medium (Evolving)

### What We Know
- **Pricing:** $15,000/month entry point (vs. our ~$25,000/month enterprise tier)
- **Features:** Hybrid cloud AI deployment, model management, monitoring
- **Timeline:** General availability announced, but no public customer references yet

### Strengths (for them)
- Aggressive pricing creates a compelling value proposition for budget-conscious buyers
- SoftSystems has established enterprise relationships through their existing product line
- Open architecture may appeal to customers wanting to avoid vendor lock-in

### Weaknesses (for them)
- No announced enterprise reference customers
- Likely limited AI model integrations compared to AI-Flow Engine's 40+ connectors
- No mention of compliance certifications (SOC 2, ISO 27001, etc.)
- Smaller support and professional services organization

### Verdict
**Not vaporware, but not yet enterprise-ready.** The platform is real and the pricing is genuinely disruptive. However, it will likely take 6-12 months for SoftSystems to build the enterprise credibility, compliance certifications, and support infrastructure needed to seriously threaten our top-tier accounts.

### Recommended Actions
1. Monitor their customer announcements over the next quarter
2. Prepare a competitive comparison document for the sales team
3. Consider whether a mid-market tier could address the pricing gap without cannibalizing enterprise revenue`,
      createdAt: '2024-03-19T15:02:00Z',
      metadata: {
        sources: ['c-9'],
        model: 'gpt-4-turbo',
        tokens: 1687,
      },
    },
  ],
  'th-4': [
    {
      id: 'm-30',
      threadId: 'th-4',
      role: 'system',
      content: `# 📝 Draft Report — March 21, 2024

**Status:** DRAFT | **Workspace:** TechCorp Inc.

> *This report is still being generated. Content may change before final publication.*

---

## Preliminary Findings

Scanning in progress. Initial analysis suggests **14 relevant articles** across 12 feeds, with early signals of new developments in EU digital sovereignty and AI safety research.

**Note:** This draft will be finalized when the next scheduled intelligence cycle completes.`,
      createdAt: '2024-03-21T04:00:05Z',
      metadata: {
        model: 'gpt-4-turbo',
        tokens: 412,
      },
    },
  ],
  'th-10': [
    {
      id: 'm-100',
      threadId: 'th-10',
      role: 'system',
      content: `# Daily Clean Energy Brief: EcoSolutions

**Date:** March 19, 2024 | **Period:** March 18–19, 2024
**Workspace:** EcoSolutions Ltd. | **Articles Scanned:** 89 | **Included:** 7

---

## Executive Summary

Today's energy landscape highlights a major **€3B EU Green Deal investment** in clean energy manufacturing, **record Q4 revenue** for competitor SolarEdge, and a **breakthrough in solid-state battery technology** from ETH Zurich.

---

## Key Developments

### 1. EU Green Deal Industrial Plan: €3B for Clean Energy Manufacturing
**Source:** EU Climate Policy News | **Score:** 92/100 | **Impact:** 🔴 High

The European Commission has announced a €3 billion investment plan targeting solar panel production, battery manufacturing, and electrolyzer capacity.

> **Opportunity:** EcoSolutions should evaluate grant and partnership opportunities under this plan, particularly for EcoStore Battery manufacturing expansion and SunPower Panels production scaling.

### 2. SolarEdge Reports Record Q4 Revenue ($780M)
**Source:** SolarEdge Blog | **Score:** 84/100 | **Impact:** 🟡 Medium

SolarEdge's record results driven by European demand (65% of revenue). Germany, Italy, and Spain leading growth.

> **Competitive Intelligence:** SolarEdge's strong European position validates the market but increases competitive pressure on our solar solutions.

### 3. Breakthrough: Solid-State Battery Achieves 500 Wh/kg
**Source:** Energy Storage News | **Score:** 87/100 | **Impact:** 🟢 Positive

ETH Zurich researchers demonstrate solid-state battery technology with energy density of 500 Wh/kg — potentially doubling EV range and improving storage capacity.

> **Strategic Implication:** If commercially viable within 3-5 years, this could revolutionize EcoStore Battery product line. Recommend establishing a research monitoring program.

---

## Recommended Actions

1. **Immediate:** Review EU Green Deal funding eligibility for current and planned manufacturing projects
2. **This Week:** Update competitive analysis with SolarEdge Q4 data
3. **This Month:** Evaluate research partnership opportunities with ETH Zurich or similar institutions
4. **Ongoing:** Monitor solid-state battery commercialization timeline`,
      createdAt: '2024-03-19T08:00:05Z',
      metadata: {
        sources: ['c-100', 'c-101', 'c-102'],
        reportId: 'rep-10',
        model: 'gpt-4-turbo',
        tokens: 2234,
      },
    },
  ],
  'th-11': [
    {
      id: 'm-110',
      threadId: 'th-11',
      role: 'system',
      content: `# Weekly Energy Intelligence: EcoSolutions

**Period:** March 11–18, 2024 | **Articles Scanned:** 178 | **Included:** 12

---

## Executive Summary

This week's key themes: **Tesla Energy's Berlin expansion**, growing **smart grid investments in Asia-Pacific**, and continued **community solar growth** across the EU. Battery recycling regulations are approaching their enforcement date.

---

## Top Stories

### 1. Tesla Energy Expands Powerwall Production in Berlin
**Source:** Reuters | **Score:** 81/100
50% capacity increase targeting 40 GWh annual European output by 2025. Direct competitive pressure on EcoStore Battery.

### 2. APAC Smart Grid Investment Reaches $12B Annually
**Source:** GreenTech Media | **Score:** 69/100
China and India driving 70% of spending. Relevant to EcoSolutions' GridMind Software APAC expansion plans.

### 3. Community Solar Projects Surge 45% in EU
**Source:** SolarPower World | **Score:** 76/100
Germany, Netherlands, and France leading adoption with strong EU funding support.

### 4. EU Battery Recycling Regulation Approaches
**Source:** EU Climate Policy News | **Score:** 74/100
January 2025 enforcement with mandatory recycled content requirements (16% cobalt, 6% lithium, 6% nickel).

### 5. Enphase Launches Next-Gen Commercial Microinverter
**Source:** Enphase Blog | **Score:** 72/100
IQ8 Commercial Microinverter supporting 350W per unit with advanced grid support features.`,
      createdAt: '2024-03-18T08:00:05Z',
      metadata: {
        sources: ['c-104', 'c-105', 'c-106', 'c-108', 'c-109'],
        reportId: 'rep-11',
        model: 'gpt-4-turbo',
        tokens: 1876,
      },
    },
  ],
  'th-12': [
    {
      id: 'm-120',
      threadId: 'th-12',
      role: 'system',
      content: `# 📝 Draft Report — March 20, 2024

**Status:** DRAFT | **Workspace:** EcoSolutions Ltd.

> *Report generation in progress. Preliminary scan indicates 8 potentially relevant articles.*

**Note:** This draft will be finalized with the next scheduled intelligence cycle.`,
      createdAt: '2024-03-20T06:00:05Z',
      metadata: {
        model: 'gpt-4-turbo',
        tokens: 298,
      },
    },
  ],
  'th-20': [
    {
      id: 'm-200',
      threadId: 'th-20',
      role: 'system',
      content: `# Last Report Before Pause: Global Retail Group

**Date:** March 1, 2024 | **Status:** Final Report Before Workspace Pause

---

## Executive Summary

This report covers the final intelligence cycle before the Global Retail Group workspace is paused for internal restructuring. Key developments include **Amazon's same-day delivery expansion**, the **$6.3 trillion e-commerce forecast**, and escalating **supply chain disruption costs**.

---

## Key Developments

### 1. Amazon Expands Same-Day Delivery to 15 New US Markets
**Source:** Amazon News Blog | **Score:** 87/100
Total same-day delivery coverage now exceeds 90 US metro areas, raising consumer delivery expectations across the retail sector.

### 2. Global E-Commerce Sales to Reach $6.3 Trillion in 2024
**Source:** E-commerce Times | **Score:** 81/100
10.4% YoY growth driven by mobile commerce, social commerce, and emerging market expansion.

### 3. Supply Chain Disruptions Cost Retailers $184B in 2023
**Source:** Supply Chain Dive | **Score:** 84/100
30% increase from 2022, driven by geopolitical tensions, extreme weather, and logistics bottlenecks.

### 4. Shopify Introduces AI-Powered Product Recommendations
**Source:** Shopify Engineering Blog | **Score:** 79/100
New AI engine analyzes customer behavior for personalized suggestions — direct challenge to retail analytics platforms.

### 5. Walmart Acquires GroceryTech for Online Grocery
**Source:** Retail Gazette UK | **Score:** 82/100
Undisclosed acquisition amount; strengthens Walmart's online grocery fulfillment capabilities.

---

## Workspace Pause Notice

This workspace will be paused following this report cycle. Monitoring will resume when restructuring is complete, estimated Q2 2024.`,
      createdAt: '2024-03-01T08:00:05Z',
      metadata: {
        sources: ['c-200', 'c-201', 'c-202', 'c-203', 'c-205'],
        reportId: 'rep-20',
        model: 'gpt-4-turbo',
        tokens: 2104,
      },
    },
  ],
  'th-21': [
    {
      id: 'm-210',
      threadId: 'th-21',
      role: 'system',
      content: `# Retail Intelligence — Feb 28, 2024

**Period:** Feb 27–28, 2024 | **Workspace:** Global Retail Group

---

## Key Developments

### 1. Walmart Acquires GroceryTech
**Source:** Retail Gazette UK | **Score:** 82/100
Walmart's acquisition of an AI-powered grocery fulfillment startup signals continued investment in online grocery capabilities.

### 2. UK Retail Sales Unexpectedly Decline 0.3% in February
**Source:** Retail Gazette UK | **Score:** 64/100
Consumer spending caution in household goods and clothing categories.

### 3. TikTok Shop Expands into Five European Markets
**Source:** Modern Retail | **Score:** 75/100
Launch in Spain, Italy, Germany, France, and Ireland intensifies social commerce competition.`,
      createdAt: '2024-02-28T08:00:05Z',
      metadata: {
        sources: ['c-205', 'c-206', 'c-207'],
        reportId: 'rep-21',
        model: 'gpt-4-turbo',
        tokens: 1245,
      },
    },
  ],
  'th-30': [
    {
      id: 'm-300',
      threadId: 'th-30',
      role: 'system',
      content: `# Daily Financial Intelligence: Apex Financial Services

**Date:** March 20, 2024 | **Period:** March 19–20, 2024
**Workspace:** Apex Financial Services | **Articles Scanned:** 124 | **Included:** 9

---

## Executive Summary

Today's financial services landscape focuses on **PSD2 enforcement updates**, **Stripe's latest payment innovations**, and ongoing **Basel IV implementation progress**. The fintech competitive landscape remains dynamic with continued investment in open banking solutions.

---

## Key Developments

### 1. PSD2 Strong Customer Authentication Enforcement Tightens
**Source:** Financial Times | **Score:** 89/100
National regulators are increasing enforcement of SCA requirements, with several major banks receiving compliance warnings.

### 2. Stripe Introduces AI-Powered Fraud Detection
**Source:** Stripe Blog | **Score:** 82/100
New machine learning models reduce false positives by 40% while maintaining detection rates.

### 3. Basel IV Implementation Timeline Clarified
**Source:** BIS Press | **Score:** 85/100
Basel Committee confirms January 2025 implementation date with transitional arrangements for smaller banks.`,
      createdAt: '2024-03-20T06:00:05Z',
      metadata: {
        reportId: 'rep-30',
        model: 'gpt-4-turbo',
        tokens: 1567,
      },
    },
  ],
  'th-31': [
    {
      id: 'm-310',
      threadId: 'th-31',
      role: 'system',
      content: `# Weekly Fintech Brief: Apex Financial Services

**Period:** March 11–18, 2024 | **Workspace:** Apex Financial Services

---

## Top Stories

### 1. Digital Currency Regulation: Central Banks Accelerate CBDC Pilots
**Source:** Bloomberg Finance | **Score:** 83/100
130+ countries now exploring CBDCs, with 11 in advanced pilot stage.

### 2. Open Banking Adoption Reaches 30% in EU
**Source:** Fintech Futures | **Score:** 78/100
Third-party API integrations growing rapidly across banking and payments sectors.

### 3. AI-Powered AML Detection Shows 60% Improvement
**Source:** Financial Times | **Score:** 80/100
New generation of anti-money laundering tools using large language models showing significant improvement over rule-based systems.`,
      createdAt: '2024-03-18T06:00:05Z',
      metadata: {
        reportId: 'rep-31',
        model: 'gpt-4-turbo',
        tokens: 1345,
      },
    },
  ],
  'th-40': [
    {
      id: 'm-400',
      threadId: 'th-40',
      role: 'system',
      content: `# Final Report: MediCore Laboratories

**Date:** February 15, 2024 | **Status:** Archived (Post-Acquisition)

---

## Note
This is the final intelligence report for MediCore Laboratories. The workspace has been archived following the acquisition of MediCore by a larger healthcare conglomerate. Data is retained for compliance purposes.

## Final Intelligence Summary

- AI in diagnostics continues to advance rapidly, with FDA approving 3 new AI-based diagnostic tools in February
- Lab automation market growth accelerating, projected 12% CAGR through 2028
- Precision medicine funding reached $2.1B in Q4 2023`,
      createdAt: '2024-02-15T08:00:05Z',
      metadata: {
        reportId: 'rep-40',
        model: 'gpt-4-turbo',
        tokens: 876,
      },
    },
  ],
};

const REGENERATE_RESPONSES = [
  `I've reconsidered the analysis from a different angle. Here's an updated assessment:

## Revised Analysis

After reviewing additional data points and cross-referencing with recent market reports, I'd like to refine my previous assessment.

**Key Changes:**
- Updated competitive positioning based on latest market share data
- Revised timeline estimates based on new regulatory information
- Additional risk factors identified in adjacent market segments

### Updated Risk Matrix

| Risk | Previous | Updated | Rationale |
|------|----------|---------|-----------|
| Market share erosion | Medium | High | Accelerated competitor spending |
| Regulatory burden | Low | Medium | New compliance requirements |
| Technology disruption | Medium | Medium-High | Faster-than-expected adoption of alternatives |

Would you like me to elaborate on any of these changes?`,

  `Let me provide an alternative perspective on this:

## Alternative Analysis

While my previous assessment focused primarily on the immediate implications, there are longer-term considerations worth noting:

1. **Market trajectory** — The current trend suggests an acceleration, not just a continuation of current patterns
2. **Second-order effects** — The competitive response may trigger a price war in adjacent segments
3. **Regulatory spillover** — EU actions often set precedents for other jurisdictions within 12-18 months

### Updated Recommendation

I'd suggest a more aggressive monitoring posture for the next quarter, with bi-weekly competitive briefings for the leadership team. Additionally, consider establishing a "rapid response" task force that can react to major competitive moves within 48 hours.

> **Confidence Level:** This analysis is based on 8 corroborating sources with an average relevance score of 0.82.`,

  `## Updated Assessment

I've incorporated additional context from recent industry reports and regulatory filings. Here's the refined view:

### Market Impact

The situation has evolved since my initial analysis. Three new data points have emerged:

- **Competitor investment** has increased 35% quarter-over-quarter (vs. my initial estimate of 20%)
- **Customer sentiment** data shows growing awareness of alternatives, with a 12% increase in competitor evaluations
- **Regulatory timeline** has been accelerated by approximately 6 months based on the latest EU Commission announcements

### Strategic Implications

These changes suggest we need to move faster on:

1. **Product differentiation** — Invest in unique capabilities that are difficult to replicate
2. **Customer lock-in** — Strengthen integration depth and switching costs
3. **Market education** — Proactively communicate our advantages before competitors set the narrative

The next 90 days are critical. I recommend scheduling a strategy review with the product and GTM teams within the next week.`,
];

function generateAgentResponse(feedback: string): string {
  const lower = feedback.toLowerCase();

  if (lower.includes('competitive') || lower.includes('competitor')) {
    return `## Competitive Intelligence Update

I've noted your emphasis on competitive intelligence. Here's what I'll do:

1. **Increase monitoring frequency** for all tagged competitor feeds (from daily to real-time where available)
2. **Lower the relevance threshold** for competitor-related content from 0.70 to 0.55
3. **Add a dedicated "Competitive Moves" section** at the top of daily reports
4. **Include competitor pricing and product launch alerts** as high-priority notifications

### Competitors Currently Tracked

| Competitor | Primary Feed | Alert Level | Last Mentioned |
|-----------|-------------|-------------|---------------|
| CloudGiant | 3 sources | High | Today |
| DataNexus | 2 sources | High | Today |
| SoftSystems | 2 sources | Medium | This week |
| NovaTech | 1 source | Low | 2 weeks ago |

Would you like me to add any additional competitors to the monitoring list, or adjust the alert thresholds?`;
  }

  if (lower.includes('regulation') || lower.includes('compliance') || lower.includes('eu')) {
    return `## Regulatory & Compliance Focus Updated

I'll increase focus on regulatory and compliance developments, particularly EU-related policy changes. Here are the adjustments:

### Enhanced Monitoring

- **EU regulatory feeds** now scanned every 4 hours (previously 12 hours)
- **Compliance impact assessments** will be included for every relevant regulatory change
- **Regulatory timeline tracker** added to weekly reports

### Upcoming Regulatory Deadlines

| Regulation | Deadline | Impact Level | Status |
|-----------|----------|-------------|--------|
| EU AI Act — Prohibited practices | Feb 2025 | High | Monitoring |
| EU AI Act — GPAI obligations | Aug 2025 | High | Monitoring |
| NIST CSF 2.0 adoption | Rolling | Medium | Active |
| EU Battery Recycling | Jan 2025 | Medium | Monitoring |

### What You'll See

Future reports will include:
1. A dedicated **Regulatory Update** section at the top of each report
2. Earlier alerts for **proposed legislation** (not just enacted)
3. **Impact assessments** mapping each regulatory change to your product lines
4. **Compliance gap analysis** recommendations

Is there a specific regulation you'd like me to track more closely?`;
  }

  if (lower.includes('more detail') || lower.includes('expand') || lower.includes('elaborate') || lower.includes('tell me more')) {
    return `## Expanded Analysis

I'll provide more detailed analysis in future reports. Here are the specific adjustments:

### Report Depth Changes

| Section | Current | Updated |
|---------|---------|---------|
| Executive summary | 3-4 bullet points | 5-6 with quantitative data |
| Key developments | 2-3 paragraphs each | 4-5 paragraphs with market context |
| Recommended actions | 3-4 items | 5-6 with priority scoring |
| Source citations | Basic | Full context and methodology |

### Additional Data Points

I'll now include in each report:
- **Market sizing data** where available (TAM, SAM, SOM estimates)
- **Historical trend lines** showing week-over-week changes
- **Competitor benchmarking** tables with direct comparisons
- **Risk-reward scoring** for each recommended action (1-10 scale)

### Example: Enhanced Development Format

> **Development:** [Title]
> **Impact Score:** 8.2/10 | **Confidence:** High (6 corroborating sources)
> **Market Context:** [2-3 sentences on broader market trends]
> **Detailed Analysis:** [4-5 paragraph deep dive with data]
> **Recommended Actions:** [Prioritized list with timeline]

This format will be applied starting with the next scheduled report. Let me know if you'd like any further adjustments!`;
  }

  if (lower.includes('less') || lower.includes('shorter') || lower.includes('concise') || lower.includes('brief')) {
    return `## Report Format Updated — Concise Mode

I'll make future reports more concise and scannable. Here are the changes:

### New Format

- **Reduced article count** to the top 5-7 most relevant (from 10-12)
- **Bullet-point format** for key findings (replacing longer paragraphs)
- **One-sentence impact summaries** instead of detailed analysis
- **Consolidated action items** at the end (instead of per-development)

### Template Preview

\`\`\`
## Quick Brief — [Date]

### Headlines
• [One-line summary of each key development]

### Impact Scores
| Development | Score | Direction |
|------------|-------|-----------|
| [Item] | 8/10 | ⬆️ Increasing |

### Actions (Top 3)
1. [Action] — [Owner] — [Timeline]
2. [Action] — [Owner] — [Timeline]
3. [Action] — [Owner] — [Timeline]
\`\`\`

### Estimated Reading Time
- **Current format:** ~8-10 minutes
- **New concise format:** ~3-4 minutes

This will apply starting with the next report cycle. Want me to adjust anything further?`;
  }

  if (lower.includes('ignore') || lower.includes('exclude') || lower.includes('don\'t') || lower.includes('skip')) {
    return `## Workspace Preferences Updated

I've updated the filtering preferences based on your feedback. Here's what changed:

### Adjusted Filters

The following topics/patterns have been **deprioritized** in relevance scoring:

- Content matching your specified exclusion criteria will have its relevance score reduced by 40%
- These items will only appear if they score above 0.85 on other criteria
- A weekly "filtered out" summary will be available if you want to review what was excluded

### Current Active Filters

| Filter | Type | Effect |
|--------|------|--------|
| Consumer hardware | Topic exclude | -40% relevance |
| Cryptocurrency | Topic exclude | -40% relevance |
| [Your new filter] | Topic exclude | -40% relevance |

> **Note:** To make these exclusions permanent and more granular, you can update the "Excluded Topics" list in the workspace settings. There you can also set exclusion strength (soft vs. hard exclude).

Would you like me to apply this change permanently to the workspace configuration?`;
  }

  if (lower.includes('summarize') || lower.includes('summary') || lower.includes('tldr') || lower.includes('tl;dr')) {
    return `## Executive Summary

Here's a concise summary of the key points from this report:

### 🎯 Top 3 Takeaways

1. **Regulatory pressure is increasing** — The EU AI Act timeline creates concrete compliance deadlines that affect your core products
2. **Competitive landscape is intensifying** — Multiple competitors are making significant moves simultaneously (CloudGiant edge expansion, SoftSystems pricing, DataNexus acquisition)
3. **Market tailwinds remain strong** — Hybrid cloud adoption (+47% YoY) and enterprise AI spending continue to validate your market thesis

### ⚡ Immediate Actions Required

- **This week:** EU AI Act compliance gap analysis
- **This week:** Competitive response strategy for CloudGiant
- **Next 2 weeks:** Customer retention outreach for at-risk accounts

### 📊 Key Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Relevant articles this period | 12 | +33% |
| Average relevance score | 0.82 | +5.6% |
| Competitor mentions | 3 | +60% |
| High-impact developments | 2 | Stable |

Need me to drill into any specific area?`;
  }

  if (lower.includes('thank') || lower.includes('great') || lower.includes('good') || lower.includes('helpful') || lower.includes('perfect')) {
    return `You're welcome! I'm glad the analysis was helpful.

### Continuous Improvement

Your positive feedback helps me refine the reporting quality. Based on your preferences, I'll continue to:

- Maintain the current level of detail and analysis depth
- Focus on actionable intelligence with clear recommendations
- Provide competitive context and market sizing data
- Include source citations for verification

> 💡 **Tip:** You can always ask me to adjust the report format, focus areas, or detail level. I learn from your feedback and apply it to future reports.

Is there anything else you'd like to explore from today's intelligence?`;
  }

  // Default response
  return `## Feedback Received

Thank you for your input: *"${feedback}"*

I've processed your feedback and will apply it to future intelligence reports. Here's what happens next:

### How Your Feedback Is Used

1. **Workspace preferences** are updated to reflect your priorities
2. **Relevance scoring** is adjusted to weight the topics you've emphasized
3. **Report generation** will incorporate your preferred format and detail level
4. **Next scheduled report** will reflect these changes

### What to Expect

- **Next daily report** will show adjustments to content selection and prioritization
- **Weekly strategic brief** will incorporate any structural changes you've requested
- You can track preference changes in the workspace settings

Is there anything specific you'd like me to focus on or adjust further? I'm here to make sure the intelligence reports are as useful as possible for your decision-making.`;
}

export async function getThread(threadId: string): Promise<ReportThread | undefined> {
  await delay(randomBetween(200, 400));
  for (const wsId in MOCK_THREADS) {
    const thread = MOCK_THREADS[wsId].find(t => t.id === threadId);
    if (thread) return { ...thread };
  }
  return undefined;
}

export async function getMessages(threadId: string): Promise<ReportMessage[]> {
  await delay(randomBetween(300, 700));
  return MOCK_MESSAGES[threadId] ? [...MOCK_MESSAGES[threadId]] : [];
}

export async function sendFeedback(threadId: string, content: string): Promise<[ReportMessage, ReportMessage]> {
  await delay(randomBetween(1200, 2200));

  const userMsg: ReportMessage = {
    id: `m-${Date.now()}`,
    threadId,
    role: 'user',
    content,
    createdAt: new Date().toISOString(),
  };

  const agentResponse = generateAgentResponse(content);

  const agentMsg: ReportMessage = {
    id: `m-${Date.now() + 1}`,
    threadId,
    role: 'agent',
    content: agentResponse,
    createdAt: new Date(Date.now() + 2000).toISOString(),
    metadata: {
      model: 'gpt-4-turbo',
      tokens: Math.floor(Math.random() * 500) + 400,
    },
  };

  if (!MOCK_MESSAGES[threadId]) MOCK_MESSAGES[threadId] = [];
  MOCK_MESSAGES[threadId].push(userMsg, agentMsg);
  return [userMsg, agentMsg];
}

export async function voteMessage(messageId: string, vote: FeedbackVote): Promise<boolean> {
  await delay(randomBetween(200, 500));
  for (const threadId in MOCK_MESSAGES) {
    const msg = MOCK_MESSAGES[threadId].find(m => m.id === messageId);
    if (msg) {
      msg.feedback = msg.feedback === vote ? undefined : vote;
      return true;
    }
  }
  return false;
}

export async function regenerateMessage(messageId: string): Promise<ReportMessage | undefined> {
  await delay(randomBetween(1500, 2800));
  for (const threadId in MOCK_MESSAGES) {
    const msgIndex = MOCK_MESSAGES[threadId].findIndex(m => m.id === messageId);
    if (msgIndex !== -1) {
      const msg = MOCK_MESSAGES[threadId][msgIndex];
      if (msg.role !== 'agent' && msg.role !== 'system') return undefined;

      const randomResponse = REGENERATE_RESPONSES[Math.floor(Math.random() * REGENERATE_RESPONSES.length)];
      const regeneratedMsg: ReportMessage = {
        ...msg,
        id: `m-${Date.now()}`,
        content: randomResponse,
        createdAt: new Date().toISOString(),
        metadata: {
          ...msg.metadata,
          regenerated: true,
          regeneratedAt: new Date().toISOString(),
          originalMessageId: messageId,
        },
      };

      MOCK_MESSAGES[threadId][msgIndex] = regeneratedMsg;
      return { ...regeneratedMsg };
    }
  }
  return undefined;
}
