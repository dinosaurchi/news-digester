import type { ContentItem, ContentItemDetail, ContentStatus, ContentType } from '@/types';
import { delay, randomBetween } from './helpers';

export const MOCK_CONTENT: Record<string, ContentItem[]> = {
  'ws-1': [
    {
      id: 'c-1', workspaceId: 'ws-1', title: 'EU AI Act Implementation Timeline Announced by European Commission',
      source: 'Reuters', sourceUrl: 'https://reuters.com/technology/eu-ai-act-timeline',
      publishedAt: '2024-03-20T09:00:00Z', type: 'news',
      relevanceScore: 0.95, llmScore: 0.92, finalScore: 0.94, status: 'included', clusterId: 'cl-1',
      snippet: 'The European Commission has published the detailed implementation timeline for the EU AI Act, with phased compliance deadlines starting in 2025.',
      body: 'The European Commission has officially published the detailed implementation timeline for the EU AI Act, marking a pivotal moment in global AI governance. The regulation, approved by the European Parliament in March 2024, establishes the world\'s most comprehensive legal framework for artificial intelligence.\n\nKey milestones include:\n- Prohibited AI practices banned from February 2025\n- General-purpose AI system obligations from August 2025\n- High-risk AI system requirements from August 2026\n\nIndustry reaction has been mixed, with tech companies expressing concern about compliance costs while civil society groups have praised the framework as a necessary safeguard.',
      inclusionReason: 'Directly relevant to TechCorp\'s AI compliance roadmap. High impact on CloudStack Pro and AI-Flow Engine product lines.',
      linkedReportIds: ['th-1'],
    },
    {
      id: 'c-2', workspaceId: 'ws-1', title: 'CloudGiant Announces 10 New Edge Data Center Locations Across Europe',
      source: 'CloudGiant Press', sourceUrl: 'https://cloudgiant.com/news/edge-expansion-2024',
      publishedAt: '2024-03-20T11:30:00Z', type: 'competitor',
      relevanceScore: 0.88, llmScore: 0.85, finalScore: 0.87, status: 'included', clusterId: 'cl-2',
      snippet: 'In a strategic move to bolster its edge presence, CloudGiant unveiled plans for 10 new data center locations across major European cities.',
      body: 'CloudGiant today announced a major expansion of its edge computing infrastructure with 10 new data center locations planned across Europe. The $2.3 billion investment will see facilities opened in London, Frankfurt, Paris, Amsterdam, Dublin, Stockholm, Zurich, Warsaw, Madrid, and Milan by Q4 2025.\n\nThe expansion directly challenges TechCorp\'s Edge-Connect Hub product line and signals CloudGiant\'s aggressive push into the enterprise edge market.',
      inclusionReason: 'Critical competitive intelligence. CloudGiant\'s edge expansion directly impacts TechCorp\'s Edge-Connect Hub market position.',
      linkedReportIds: ['th-1', 'th-3'],
    },
    {
      id: 'c-3', workspaceId: 'ws-1', title: '10 Best Gaming Laptops of 2024',
      source: 'PC Gamer', sourceUrl: 'https://pcgamer.com/best-laptops-2024',
      publishedAt: '2024-03-20T08:00:00Z', type: 'article',
      relevanceScore: 0.1, llmScore: 0.05, finalScore: 0.07, status: 'excluded',
      snippet: 'We review the top performing gaming laptops currently on the market, from budget options to high-end gaming beasts.',
      exclusionReason: 'Consumer hardware content. Topic explicitly excluded from workspace profile.',
    },
    {
      id: 'c-4', workspaceId: 'ws-1', title: 'Hybrid Cloud Adoption Surges 47% Among Fortune 500 Companies',
      source: 'Cloud News Daily', sourceUrl: 'https://cloudnews.com/hybrid-cloud-surge',
      publishedAt: '2024-03-20T07:00:00Z', type: 'news',
      relevanceScore: 0.91, llmScore: 0.88, finalScore: 0.90, status: 'included', clusterId: 'cl-3',
      snippet: 'A new industry survey reveals that 47% of Fortune 500 companies have adopted hybrid cloud strategies in the past year.',
      body: 'The 2024 Enterprise Cloud Adoption Report reveals a dramatic shift in infrastructure strategies among the world\'s largest companies. Hybrid cloud adoption has surged 47% year-over-year, with 78% of respondents citing AI workload requirements as the primary driver.\n\nKey findings:\n- Multi-cloud strategies now preferred by 62% of enterprises\n- Average annual cloud spend increased to $4.2M per company\n- Security and compliance remain the top concerns (cited by 89%)',
      inclusionReason: 'Directly validates TechCorp\'s hybrid cloud focus. Market data supports CloudStack Pro positioning.',
      linkedReportIds: ['th-1'],
    },
    {
      id: 'c-5', workspaceId: 'ws-1', title: 'DataNexus Acquires AI Security Startup for $340M',
      source: 'TechCrunch', sourceUrl: 'https://techcrunch.com/2024/03/19/datanexus-acquires-ai-security-startup',
      publishedAt: '2024-03-19T16:00:00Z', type: 'news',
      relevanceScore: 0.86, llmScore: 0.83, finalScore: 0.85, status: 'included', clusterId: 'cl-4',
      snippet: 'DataNexus Corp. has completed the acquisition of SecureAI, a cybersecurity startup specializing in AI threat detection.',
      body: 'DataNexus Corp. announced today it has acquired SecureAI, a three-year-old cybersecurity startup, for $340 million in cash and stock. SecureAI\'s AI-powered threat detection platform will be integrated into DataNexus\'s enterprise security suite, directly competing with TechCorp\'s DataGuard Shield product.\n\nThe acquisition is DataNexus\'s third major deal this year and signals an escalating battle in the AI security market.',
      inclusionReason: 'Major competitive move by DataNexus. Acquisition of AI security capabilities directly impacts TechCorp\'s DataGuard Shield.',
      linkedReportIds: ['th-3'],
    },
    {
      id: 'c-6', workspaceId: 'ws-1', title: 'New NIST Cybersecurity Framework 2.0 Released',
      source: 'Wired', sourceUrl: 'https://wired.com/security/nist-framework-2',
      publishedAt: '2024-03-19T14:00:00Z', type: 'news',
      relevanceScore: 0.82, llmScore: 0.79, finalScore: 0.81, status: 'included', clusterId: 'cl-5',
      snippet: 'NIST has released the much-anticipated Cybersecurity Framework 2.0, with significant updates to supply chain security and governance requirements.',
      body: 'The National Institute of Standards and Technology (NIST) has officially released Cybersecurity Framework 2.0, the first major update since 2014. The new framework introduces enhanced focus areas including supply chain risk management, governance, and the integration of emerging technologies.\n\nFor enterprise cloud providers like TechCorp, the framework introduces new compliance considerations that will need to be addressed in product offerings.',
      inclusionReason: 'Regulatory update impacting TechCorp\'s cybersecurity compliance posture and DataGuard Shield roadmap.',
      linkedReportIds: ['th-1'],
    },
    {
      id: 'c-7', workspaceId: 'ws-1', title: 'Bitcoin Surges Past $70,000 Mark',
      source: 'CoinDesk', sourceUrl: 'https://coindesk.com/markets/bitcoin-70k',
      publishedAt: '2024-03-19T12:00:00Z', type: 'news',
      relevanceScore: 0.05, llmScore: 0.03, finalScore: 0.04, status: 'excluded',
      snippet: 'Bitcoin has reached a new all-time high, surpassing $70,000 for the first time in history.',
      exclusionReason: 'Cryptocurrency content. Topic explicitly excluded from workspace profile.',
    },
    {
      id: 'c-8', workspaceId: 'ws-1', title: 'Kubernetes 1.30 Introduces Advanced GPU Scheduling',
      source: 'Kubernetes Blog', sourceUrl: 'https://kubernetes.io/blog/2024/03/19/kubernetes-1-30',
      publishedAt: '2024-03-19T10:00:00Z', type: 'blog',
      relevanceScore: 0.72, llmScore: 0.68, finalScore: 0.70, status: 'included', clusterId: 'cl-6',
      snippet: 'The latest Kubernetes release includes major improvements to GPU resource scheduling, benefiting AI and ML workloads.',
      body: 'Kubernetes 1.30, released this week, introduces significant enhancements to GPU scheduling and management. The new features include dynamic GPU partitioning, improved multi-GPU pod scheduling, and native support for NVIDIA and AMD GPU architectures.\n\nThese improvements are particularly relevant for enterprises running AI inference workloads on containerized infrastructure.',
      inclusionReason: 'Infrastructure advancement relevant to TechCorp\'s cloud platform strategy and AI-Flow Engine deployment.',
      linkedReportIds: ['th-2'],
    },
    {
      id: 'c-9', workspaceId: 'ws-1', title: 'SoftSystems Launches Enterprise AI Platform to Compete with CloudStack',
      source: 'SoftSystems Blog', sourceUrl: 'https://softsystems.io/blog/enterprise-ai-launch',
      publishedAt: '2024-03-19T08:00:00Z', type: 'competitor',
      relevanceScore: 0.84, llmScore: 0.80, finalScore: 0.82, status: 'included', clusterId: 'cl-7',
      snippet: 'SoftSystems International has unveiled its Enterprise AI Platform, directly targeting the cloud AI infrastructure market.',
      body: 'SoftSystems International today launched its Enterprise AI Platform, a comprehensive solution designed to help businesses deploy and manage AI workloads across hybrid cloud environments. The platform directly competes with TechCorp\'s CloudStack Pro and AI-Flow Engine.\n\nPricing starts at $15,000/month, significantly undercutting TechCorp\'s enterprise tier.',
      inclusionReason: 'Direct competitive threat. SoftSystems entering TechCorp\'s core market with aggressive pricing.',
      linkedReportIds: ['th-3'],
    },
    {
      id: 'c-10', workspaceId: 'ws-1', title: 'Gartner Predicts 80% of Enterprises Will Use GenAI by 2026',
      source: 'Gartner', sourceUrl: 'https://gartner.com/smarterwithgartner/genai-predictions',
      publishedAt: '2024-03-18T15:00:00Z', type: 'article',
      relevanceScore: 0.78, llmScore: 0.75, finalScore: 0.77, status: 'included', clusterId: 'cl-3',
      snippet: 'A new Gartner report forecasts that 80% of enterprises will have deployed generative AI applications by 2026.',
      body: 'Gartner\'s latest research predicts that generative AI will be a standard feature in 80% of enterprise software offerings by 2026. The report highlights that early adopters are already seeing significant productivity gains, particularly in customer service, content generation, and code development.\n\nThe findings underscore the market opportunity for TechCorp\'s AI-Flow Engine.',
      inclusionReason: 'Market validation for TechCorp\'s generative AI product strategy.',
      linkedReportIds: ['th-2'],
    },
    {
      id: 'c-11', workspaceId: 'ws-1', title: 'Edge Computing Market to Reach $61.4B by 2028',
      source: 'MarketsandMarkets', sourceUrl: 'https://marketsandmarkets.com/edge-computing-forecast',
      publishedAt: '2024-03-18T12:00:00Z', type: 'press_release',
      relevanceScore: 0.73, llmScore: 0.70, finalScore: 0.72, status: 'included', clusterId: 'cl-2',
      snippet: 'A new market research report projects the edge computing market will grow at a CAGR of 25.3% through 2028.',
      body: 'The global edge computing market is projected to grow from $15.9 billion in 2023 to $61.4 billion by 2028, representing a compound annual growth rate (CAGR) of 25.3%, according to a new report from MarketsandMarkets.\n\nKey growth drivers include the proliferation of IoT devices, the need for real-time data processing, and the expansion of 5G networks.',
      inclusionReason: 'Market sizing data supporting TechCorp\'s edge computing investment thesis.',
      linkedReportIds: ['th-2'],
    },
    {
      id: 'c-12', workspaceId: 'ws-1', title: 'CloudGiant and DataNexus Announce Strategic Partnership',
      source: 'CloudGiant Press', sourceUrl: 'https://cloudgiant.com/news/datanexus-partnership',
      publishedAt: '2024-03-18T09:00:00Z', type: 'competitor',
      relevanceScore: 0.89, llmScore: 0.86, finalScore: 0.88, status: 'included', clusterId: 'cl-4',
      snippet: 'CloudGiant and DataNexus have formed a strategic alliance to integrate their cloud and security platforms.',
      body: 'In a move that significantly reshapes the competitive landscape, CloudGiant and DataNexus today announced a strategic partnership to integrate their respective cloud infrastructure and cybersecurity platforms. The combined offering will provide enterprises with a unified solution for cloud management, AI deployment, and security.\n\nThe partnership creates a formidable competitor to TechCorp\'s integrated CloudStack + DataGuard portfolio.',
      inclusionReason: 'Major competitive development. Partnership between two key competitors creates combined threat.',
      linkedReportIds: ['th-3'],
    },
    {
      id: 'c-13', workspaceId: 'ws-1', title: 'EU Announces €2B Investment in Sovereign Cloud Infrastructure',
      source: 'EU Regulatory Digest', sourceUrl: 'https://euregulatorydigest.com/sovereign-cloud-investment',
      publishedAt: '2024-03-17T14:00:00Z', type: 'news',
      relevanceScore: 0.80, llmScore: 0.77, finalScore: 0.79, status: 'included', clusterId: 'cl-8',
      snippet: 'The European Commission has announced a €2 billion investment plan to build sovereign cloud infrastructure across the EU.',
      body: 'The European Commission unveiled a €2 billion investment plan to develop sovereign cloud computing infrastructure across the European Union. The initiative, part of the broader EU Digital Strategy, aims to reduce dependency on non-European cloud providers and ensure data sovereignty for EU citizens and businesses.\n\nThe plan includes funding for three new cloud regions and partnerships with European cloud providers.',
      inclusionReason: 'Significant regulatory and market development for TechCorp\'s EU operations.',
      linkedReportIds: ['th-1', 'th-2'],
    },
    {
      id: 'c-14', workspaceId: 'ws-1', title: 'NovaTech Releases Open-Source AI Orchestration Tool',
      source: 'NovaTech Blog', sourceUrl: 'https://novatech.com/blog/open-source-ai-orchestration',
      publishedAt: '2024-03-17T10:00:00Z', type: 'competitor',
      relevanceScore: 0.68, llmScore: 0.65, finalScore: 0.67, status: 'included',
      snippet: 'NovaTech Solutions has released an open-source AI orchestration tool that competes with proprietary solutions.',
      body: 'NovaTech Solutions has released "NovaFlow", an open-source AI orchestration tool that provides many of the features found in proprietary solutions like TechCorp\'s AI-Flow Engine. The tool is available under the Apache 2.0 license and has already garnered 2,000+ stars on GitHub.',
      inclusionReason: 'Open-source competitive threat to AI-Flow Engine product line.',
      linkedReportIds: ['th-2'],
    },
    {
      id: 'c-15', workspaceId: 'ws-1', title: 'How AI is Transforming Healthcare Diagnostics',
      source: 'Nature Medicine', sourceUrl: 'https://nature.com/articles/ai-healthcare-diagnostics',
      publishedAt: '2024-03-17T08:00:00Z', type: 'article',
      relevanceScore: 0.25, llmScore: 0.20, finalScore: 0.23, status: 'excluded',
      snippet: 'A comprehensive review of AI applications in medical diagnostics, from radiology to pathology.',
      exclusionReason: 'Healthcare-specific content. Outside TechCorp\'s enterprise cloud and AI focus areas.',
    },
    {
      id: 'c-16', workspaceId: 'ws-1', title: 'Cybersecurity Attack Surface Expands with AI-Powered Threats',
      source: 'Ars Technica', sourceUrl: 'https://arstechnica.com/security/ai-powered-threats',
      publishedAt: '2024-03-16T16:00:00Z', type: 'news',
      relevanceScore: 0.76, llmScore: 0.73, finalScore: 0.75, status: 'included', clusterId: 'cl-5',
      snippet: 'Security researchers warn that AI-powered cyberattacks are becoming more sophisticated and harder to detect.',
      body: 'Security researchers at multiple leading firms have documented a significant increase in AI-powered cyberattacks. The new generation of threats uses large language models to craft more convincing phishing emails, automate vulnerability discovery, and evade traditional security systems.\n\nThe trend underscores the growing importance of AI-powered defense solutions like TechCorp\'s DataGuard Shield.',
      inclusionReason: 'Threat landscape evolution relevant to DataGuard Shield positioning.',
      linkedReportIds: ['th-1'],
    },
    {
      id: 'c-17', workspaceId: 'ws-1', title: 'The Future of Remote Work: Trends for 2024 and Beyond',
      source: 'Harvard Business Review', sourceUrl: 'https://hbr.org/remote-work-trends-2024',
      publishedAt: '2024-03-16T10:00:00Z', type: 'article',
      relevanceScore: 0.15, llmScore: 0.12, finalScore: 0.14, status: 'excluded',
      snippet: 'An analysis of evolving remote work patterns and their implications for enterprise technology spending.',
      exclusionReason: 'General workplace trend. Low direct relevance to TechCorp\'s product and competitive landscape.',
    },
    {
      id: 'c-18', workspaceId: 'ws-1', title: 'Multi-Cloud Cost Optimization: Strategies for Enterprise',
      source: 'Cloud News Daily', sourceUrl: 'https://cloudnews.com/multi-cloud-cost-optimization',
      publishedAt: '2024-03-16T07:00:00Z', type: 'article',
      relevanceScore: 0.69, llmScore: 0.66, finalScore: 0.68, status: 'pending',
      snippet: 'Enterprise IT leaders share their strategies for managing and reducing multi-cloud infrastructure costs.',
      body: 'As enterprises increasingly adopt multi-cloud strategies, managing costs across different providers has become a critical challenge. This article examines cost optimization strategies employed by leading companies.',
      inclusionReason: 'Cost optimization is a growing concern for CloudStack Pro customers.',
    },
    {
      id: 'c-19', workspaceId: 'ws-1', title: 'AWS Re:Invent 2024 Keynote Announces New AI Chip Trainium2',
      source: 'AWS Blog', sourceUrl: 'https://aws.amazon.com/blogs/aws/reinvent-2024-trainium2',
      publishedAt: '2024-03-15T14:00:00Z', type: 'social',
      relevanceScore: 0.62, llmScore: 0.58, finalScore: 0.60, status: 'pending', clusterId: 'cl-6',
      snippet: 'AWS announced Trainium2, its next-generation AI training chip, at Re:Invent 2024 with 4x performance improvements.',
      body: 'At Re:Invent 2024, AWS unveiled Trainium2, its next-generation purpose-built AI training chip. The chip promises 4x the training performance of its predecessor and is designed to compete directly with NVIDIA\'s H100.',
    },
    {
      id: 'c-20', workspaceId: 'ws-1', title: 'TechCorp CEO Discusses Enterprise AI Strategy at Davos Forum',
      source: 'LinkedIn', sourceUrl: 'https://linkedin.com/posts/techcorp-ceo-davos-2024',
      publishedAt: '2024-03-14T10:00:00Z', type: 'social',
      relevanceScore: 0.55, llmScore: 0.50, finalScore: 0.53, status: 'pending',
      snippet: 'TechCorp CEO shared the company\'s vision for responsible enterprise AI deployment at the World Economic Forum.',
      body: 'Speaking at a panel on AI governance at Davos, TechCorp\'s CEO outlined the company\'s three-pillar approach to enterprise AI: transparency, compliance, and human oversight.',
      exclusionReason: 'Self-referential content. Low analytical value for competitive intelligence.',
    },
  ],
  'ws-2': [
    {
      id: 'c-100', workspaceId: 'ws-2', title: 'EU Green Deal Industrial Plan: €3B for Clean Energy Manufacturing',
      source: 'EU Climate Policy News', sourceUrl: 'https://euclimatepolicy.eu/green-deal-industrial-plan',
      publishedAt: '2024-03-19T10:00:00Z', type: 'news',
      relevanceScore: 0.93, llmScore: 0.90, finalScore: 0.92, status: 'included', clusterId: 'cl-20',
      snippet: 'The European Commission has unveiled a €3 billion investment plan under the Green Deal Industrial Plan to boost clean energy manufacturing.',
      body: 'The European Commission has announced a comprehensive €3 billion investment plan designed to strengthen Europe\'s clean energy manufacturing base. The plan targets solar panel production, battery manufacturing, and electrolyzer capacity.',
      inclusionReason: 'Directly impacts EcoSolutions\' manufacturing strategy and market opportunity.',
      linkedReportIds: ['th-10'],
    },
    {
      id: 'c-101', workspaceId: 'ws-2', title: 'SolarEdge Reports Record Q4 Revenue Driven by European Demand',
      source: 'SolarEdge Blog', sourceUrl: 'https://solaredge.com/blog/q4-2024-results',
      publishedAt: '2024-03-19T08:00:00Z', type: 'competitor',
      relevanceScore: 0.85, llmScore: 0.82, finalScore: 0.84, status: 'included', clusterId: 'cl-21',
      snippet: 'SolarEdge Technologies reported record Q4 revenue of $780M, with European markets accounting for 65% of sales.',
      body: 'SolarEdge Technologies announced record fourth-quarter revenue of $780 million, driven primarily by strong demand across European markets. European sales accounted for 65% of total revenue, with Germany, Italy, and Spain leading growth.',
      inclusionReason: 'Competitive intelligence. SolarEdge\'s strong European performance signals market opportunity.',
      linkedReportIds: ['th-10'],
    },
    {
      id: 'c-102', workspaceId: 'ws-2', title: 'Breakthrough in Solid-State Battery Technology Achieves 500 Wh/kg',
      source: 'Energy Storage News', sourceUrl: 'https://energystorage.news/solid-state-breakthrough',
      publishedAt: '2024-03-18T14:00:00Z', type: 'news',
      relevanceScore: 0.88, llmScore: 0.85, finalScore: 0.87, status: 'included', clusterId: 'cl-22',
      snippet: 'Researchers at a European university have achieved a breakthrough in solid-state battery technology with energy density of 500 Wh/kg.',
      body: 'A team of researchers at ETH Zurich has achieved a significant breakthrough in solid-state battery technology, demonstrating energy density of 500 Wh/kg in laboratory conditions. The new battery technology could potentially double the range of electric vehicles and dramatically improve energy storage capacity.',
      inclusionReason: 'Technology breakthrough with direct implications for EcoSolutions\' battery storage roadmap.',
      linkedReportIds: ['th-10'],
    },
    {
      id: 'c-103', workspaceId: 'ws-2', title: 'Global Solar Panel Prices Drop 30% in Past Year',
      source: 'Renewable Energy World', sourceUrl: 'https://renewableenergyworld.com/solar-price-drop',
      publishedAt: '2024-03-18T10:00:00Z', type: 'news',
      relevanceScore: 0.79, llmScore: 0.76, finalScore: 0.78, status: 'included',
      snippet: 'Falling solar panel prices driven by manufacturing overcapacity in Asia are reshaping the global market.',
      body: 'Global solar panel prices have fallen by approximately 30% over the past year, driven primarily by manufacturing overcapacity in China and Southeast Asia. The price decline is creating both opportunities and challenges for European manufacturers like EcoSolutions.',
      inclusionReason: 'Pricing trend directly impacting EcoSolutions\' SunPower Panels competitive positioning.',
      linkedReportIds: ['th-10'],
    },
    {
      id: 'c-104', workspaceId: 'ws-2', title: 'Tesla Energy Expands Powerwall Production in Berlin',
      source: 'Reuters', sourceUrl: 'https://reuters.com/business/tesla-energy-berlin',
      publishedAt: '2024-03-17T12:00:00Z', type: 'competitor',
      relevanceScore: 0.82, llmScore: 0.79, finalScore: 0.81, status: 'included', clusterId: 'cl-23',
      snippet: 'Tesla Energy has begun expanding its Powerwall battery production capacity at its Berlin Gigafactory.',
      body: 'Tesla Energy has commenced expansion of its Powerwall battery production at the Berlin Gigafactory, targeting a 50% increase in annual output. The expansion will bring total European battery storage capacity to 40 GWh annually.',
      inclusionReason: 'Competitive intelligence. Tesla\'s European expansion directly impacts EcoSolutions\' battery market.',
      linkedReportIds: ['th-11'],
    },
    {
      id: 'c-105', workspaceId: 'ws-2', title: 'New EU Battery Recycling Regulation Takes Effect',
      source: 'EU Climate Policy News', sourceUrl: 'https://euclimatepolicy.eu/battery-recycling-regulation',
      publishedAt: '2024-03-17T09:00:00Z', type: 'news',
      relevanceScore: 0.75, llmScore: 0.72, finalScore: 0.74, status: 'included',
      snippet: 'New EU battery recycling regulations require manufacturers to use minimum recycled content in new batteries from 2025.',
      body: 'New EU battery recycling regulations, effective from January 2025, mandate minimum recycled content requirements for new batteries sold in the European market. The regulations require 16% recycled cobalt, 6% recycled lithium, and 6% recycled nickel in new batteries.',
      inclusionReason: 'Regulatory compliance requirement for EcoSolutions\' EcoStore Battery product line.',
      linkedReportIds: ['th-10'],
    },
    {
      id: 'c-106', workspaceId: 'ws-2', title: 'Smart Grid Investment in Asia-Pacific Reaches $12B Annually',
      source: 'GreenTech Media', sourceUrl: 'https://greentechmedia.com/smart-grid-asia-investment',
      publishedAt: '2024-03-16T14:00:00Z', type: 'news',
      relevanceScore: 0.70, llmScore: 0.67, finalScore: 0.69, status: 'included',
      snippet: 'Asia-Pacific smart grid investments have reached $12 billion annually, with China and India leading adoption.',
      body: 'Annual smart grid investments in the Asia-Pacific region have reached $12 billion, according to a new report from BloombergNEF. China and India account for over 70% of the spending, driven by grid modernization and renewable energy integration programs.',
      inclusionReason: 'Market intelligence for EcoSolutions\' APAC expansion strategy.',
      linkedReportIds: ['th-11'],
    },
    {
      id: 'c-107', workspaceId: 'ws-2', title: 'Oil and Gas Industry Invests in Carbon Capture Technology',
      source: 'Financial Times', sourceUrl: 'https://ft.com/energy/carbon-capture-investment',
      publishedAt: '2024-03-16T08:00:00Z', type: 'news',
      relevanceScore: 0.30, llmScore: 0.25, finalScore: 0.28, status: 'excluded',
      snippet: 'Major oil and gas companies have committed $8 billion to carbon capture and storage projects.',
      exclusionReason: 'Fossil fuel industry content. Limited direct relevance to EcoSolutions\' clean energy focus.',
    },
    {
      id: 'c-108', workspaceId: 'ws-2', title: 'Community Solar Projects Surge 45% in EU Member States',
      source: 'SolarPower World', sourceUrl: 'https://solarpowerworldonline.com/community-solar-eu',
      publishedAt: '2024-03-15T12:00:00Z', type: 'news',
      relevanceScore: 0.77, llmScore: 0.74, finalScore: 0.76, status: 'included',
      snippet: 'Community solar installations across EU member states have grown 45% year-over-year.',
      body: 'Community solar installations across the European Union have grown by 45% year-over-year, with Germany, the Netherlands, and France leading adoption. The growth is supported by EU funding programs and favorable regulatory frameworks.',
      inclusionReason: 'Market growth data relevant to EcoSolutions\' SunPower Panels distribution strategy.',
      linkedReportIds: ['th-11'],
    },
    {
      id: 'c-109', workspaceId: 'ws-2', title: 'Enphase Energy Launches Next-Gen Microinverter for Commercial Solar',
      source: 'Enphase Blog', sourceUrl: 'https://enphase.com/blog/next-gen-microinverter',
      publishedAt: '2024-03-15T09:00:00Z', type: 'competitor',
      relevanceScore: 0.73, llmScore: 0.70, finalScore: 0.72, status: 'included', clusterId: 'cl-24',
      snippet: 'Enphase Energy has introduced its next-generation microinverter designed for commercial solar installations.',
      body: 'Enphase Energy has launched the IQ8 Commercial Microinverter, designed for high-power commercial solar installations. The new microinverter supports up to 350W per unit and features advanced grid support capabilities.',
      inclusionReason: 'Competitive product launch relevant to EcoSolutions\' inverter partnerships.',
      linkedReportIds: ['th-11'],
    },
  ],
  'ws-3': [
    {
      id: 'c-200', workspaceId: 'ws-3', title: 'Amazon Launches Same-Day Delivery in 15 New US Markets',
      source: 'Amazon News Blog', sourceUrl: 'https://amazon.com/about/news/same-day-delivery',
      publishedAt: '2024-03-01T10:00:00Z', type: 'competitor',
      relevanceScore: 0.88, llmScore: 0.85, finalScore: 0.87, status: 'included', clusterId: 'cl-30',
      snippet: 'Amazon has expanded same-day delivery to 15 additional US metropolitan areas.',
      body: 'Amazon has expanded its same-day delivery service to 15 additional US metropolitan areas, bringing the total to over 90 markets nationwide. The expansion puts additional pressure on traditional retailers to match delivery speeds.',
      inclusionReason: 'Competitive move raising the bar for delivery expectations in retail.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-201', workspaceId: 'ws-3', title: 'Global E-commerce Sales Expected to Reach $6.3 Trillion in 2024',
      source: 'E-commerce Times', sourceUrl: 'https://ecommercetimes.com/global-ecommerce-forecast-2024',
      publishedAt: '2024-03-01T08:00:00Z', type: 'news',
      relevanceScore: 0.82, llmScore: 0.79, finalScore: 0.81, status: 'included',
      snippet: 'New forecasts predict global e-commerce sales will surpass $6.3 trillion in 2024.',
      body: 'Global e-commerce sales are projected to reach $6.3 trillion in 2024, representing a 10.4% increase over 2023, according to eMarketer\'s latest forecast. The growth is driven by mobile commerce, social commerce, and continued expansion in emerging markets.',
      inclusionReason: 'Market sizing data for Global Retail Group\'s e-commerce strategy.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-202', workspaceId: 'ws-3', title: 'Shopify Introduces AI-Powered Product Recommendations',
      source: 'Shopify Engineering Blog', sourceUrl: 'https://shopify.com/engineering/ai-recommendations',
      publishedAt: '2024-03-01T07:00:00Z', type: 'competitor',
      relevanceScore: 0.80, llmScore: 0.77, finalScore: 0.79, status: 'included', clusterId: 'cl-31',
      snippet: 'Shopify has launched a new AI-powered product recommendation engine for its merchant platform.',
      body: 'Shopify has introduced an AI-powered product recommendation engine that analyzes customer behavior patterns to deliver personalized product suggestions. The feature is available to all Shopify merchants and represents a direct challenge to traditional retail analytics platforms.',
      inclusionReason: 'Competitive product development in retail analytics space.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-203', workspaceId: 'ws-3', title: 'Supply Chain Disruptions Cost Retailers $184B in 2023',
      source: 'Supply Chain Dive', sourceUrl: 'https://supplychaindive.com/supply-chain-costs-2023',
      publishedAt: '2024-02-29T14:00:00Z', type: 'news',
      relevanceScore: 0.85, llmScore: 0.82, finalScore: 0.84, status: 'included',
      snippet: 'A new industry report estimates that supply chain disruptions cost global retailers $184 billion in 2023.',
      body: 'Supply chain disruptions cost global retailers an estimated $184 billion in 2023, according to a report from the MIT Center for Transportation & Logistics. The figure represents a 30% increase from 2022, driven by geopolitical tensions, extreme weather events, and ongoing logistics bottlenecks.',
      inclusionReason: 'Supply chain challenges directly relevant to Global Retail Group\'s operations.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-204', workspaceId: 'ws-3', title: 'Retail Dive Analysis: Omnichannel Strategies That Work in 2024',
      source: 'Retail Dive', sourceUrl: 'https://retaildive.com/news/omnichannel-strategies-2024',
      publishedAt: '2024-02-29T10:00:00Z', type: 'article',
      relevanceScore: 0.78, llmScore: 0.75, finalScore: 0.77, status: 'included',
      snippet: 'An in-depth analysis of successful omnichannel retail strategies employed by leading brands.',
      body: 'This analysis examines how leading retailers are implementing omnichannel strategies, including unified inventory management, clienteling, and seamless returns across channels.',
      inclusionReason: 'Strategic analysis relevant to Global Retail Group\'s omnichannel initiatives.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-205', workspaceId: 'ws-3', title: 'Walmart Acquires Tech Startup to Boost Online Grocery',
      source: 'Retail Gazette UK', sourceUrl: 'https://retailgazette.co.uk/walmart-grocery-acquisition',
      publishedAt: '2024-02-28T12:00:00Z', type: 'competitor',
      relevanceScore: 0.83, llmScore: 0.80, finalScore: 0.82, status: 'included', clusterId: 'cl-30',
      snippet: 'Walmart has acquired a grocery technology startup to enhance its online grocery delivery capabilities.',
      body: 'Walmart has acquired GroceryTech, a startup specializing in AI-powered grocery fulfillment and delivery optimization, for an undisclosed amount. The acquisition will strengthen Walmart\'s online grocery platform.',
      inclusionReason: 'Walmart competitive move in online grocery segment.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-206', workspaceId: 'ws-3', title: 'UK Retail Sales Show Unexpected Decline in February',
      source: 'Retail Gazette UK', sourceUrl: 'https://retailgazette.co.uk/uk-retail-sales-feb',
      publishedAt: '2024-02-28T09:00:00Z', type: 'news',
      relevanceScore: 0.65, llmScore: 0.62, finalScore: 0.64, status: 'included',
      snippet: 'UK retail sales unexpectedly fell 0.3% in February, raising concerns about consumer spending.',
      body: 'UK retail sales fell by 0.3% in February, confounding economist expectations of a 0.4% increase. The decline was driven by reduced spending on household goods and clothing, suggesting ongoing consumer caution.',
      inclusionReason: 'Market conditions relevant to Global Retail Group\'s UK operations.',
      linkedReportIds: ['th-20'],
    },
    {
      id: 'c-207', workspaceId: 'ws-3', title: 'TikTok Shop Expands into Five New European Markets',
      source: 'Modern Retail', sourceUrl: 'https://modernretail.com/tiktok-shop-europe-expansion',
      publishedAt: '2024-02-28T07:00:00Z', type: 'news',
      relevanceScore: 0.76, llmScore: 0.73, finalScore: 0.75, status: 'included',
      snippet: 'TikTok Shop is expanding into five new European markets, intensifying social commerce competition.',
      body: 'TikTok Shop has launched in five new European markets: Spain, Italy, Germany, France, and Ireland. The expansion brings social commerce to millions of new European consumers.',
      inclusionReason: 'Social commerce expansion creating new competitive dynamics in European retail.',
      linkedReportIds: ['th-20'],
    },
  ],
};

export const MOCK_CONTENT_DETAILS: Record<string, ContentItemDetail> = {
  'c-1': {
    id: 'c-1', workspaceId: 'ws-1', title: 'EU AI Act Implementation Timeline Announced by European Commission',
    source: 'Reuters', sourceUrl: 'https://reuters.com/technology/eu-ai-act-timeline',
    publishedAt: '2024-03-20T09:00:00Z', type: 'news',
    relevanceScore: 0.95, llmScore: 0.92, finalScore: 0.94, status: 'included', clusterId: 'cl-1',
    snippet: 'The European Commission has published the detailed implementation timeline for the EU AI Act, with phased compliance deadlines starting in 2025.',
    body: 'The European Commission has officially published the detailed implementation timeline for the EU AI Act, marking a pivotal moment in global AI governance. The regulation, approved by the European Parliament in March 2024, establishes the world\'s most comprehensive legal framework for artificial intelligence.\n\nKey milestones include:\n- Prohibited AI practices banned from February 2025\n- General-purpose AI system obligations from August 2025\n- High-risk AI system requirements from August 2026\n\nIndustry reaction has been mixed, with tech companies expressing concern about compliance costs while civil society groups have praised the framework as a necessary safeguard.',
    inclusionReason: 'Directly relevant to TechCorp\'s AI compliance roadmap. High impact on CloudStack Pro and AI-Flow Engine product lines.',
    linkedReportIds: ['th-1'],
    scoreBreakdown: { relevance: 0.96, llm: 0.92, freshness: 0.98, sourceAuthority: 0.95 },
    clusterItems: [
      { id: 'c-1b', workspaceId: 'ws-1', title: 'EU Parliament Vote on AI Act: What It Means for Enterprise Software', source: 'Politico', sourceUrl: 'https://politico.eu/eu-ai-act-vote', publishedAt: '2024-03-20T07:00:00Z', type: 'news', relevanceScore: 0.91, llmScore: 0.88, finalScore: 0.90, status: 'included', clusterId: 'cl-1', snippet: 'The European Parliament\'s vote on the AI Act has significant implications for enterprise software companies operating in the EU.' },
    ],
  },
  'c-2': {
    id: 'c-2', workspaceId: 'ws-1', title: 'CloudGiant Announces 10 New Edge Data Center Locations Across Europe',
    source: 'CloudGiant Press', sourceUrl: 'https://cloudgiant.com/news/edge-expansion-2024',
    publishedAt: '2024-03-20T11:30:00Z', type: 'competitor',
    relevanceScore: 0.88, llmScore: 0.85, finalScore: 0.87, status: 'included', clusterId: 'cl-2',
    snippet: 'In a strategic move to bolster its edge presence, CloudGiant unveiled plans for 10 new data center locations across major European cities.',
    body: 'CloudGiant today announced a major expansion of its edge computing infrastructure with 10 new data center locations planned across Europe. The $2.3 billion investment will see facilities opened in London, Frankfurt, Paris, Amsterdam, Dublin, Stockholm, Zurich, Warsaw, Madrid, and Milan by Q4 2025.\n\nThe expansion directly challenges TechCorp\'s Edge-Connect Hub product line and signals CloudGiant\'s aggressive push into the enterprise edge market.',
    inclusionReason: 'Critical competitive intelligence. CloudGiant\'s edge expansion directly impacts TechCorp\'s Edge-Connect Hub market position.',
    linkedReportIds: ['th-1', 'th-3'],
    scoreBreakdown: { relevance: 0.90, llm: 0.85, freshness: 0.92, sourceAuthority: 0.80 },
  },
  'c-100': {
    id: 'c-100', workspaceId: 'ws-2', title: 'EU Green Deal Industrial Plan: €3B for Clean Energy Manufacturing',
    source: 'EU Climate Policy News', sourceUrl: 'https://euclimatepolicy.eu/green-deal-industrial-plan',
    publishedAt: '2024-03-19T10:00:00Z', type: 'news',
    relevanceScore: 0.93, llmScore: 0.90, finalScore: 0.92, status: 'included', clusterId: 'cl-20',
    snippet: 'The European Commission has unveiled a €3 billion investment plan under the Green Deal Industrial Plan to boost clean energy manufacturing.',
    body: 'The European Commission has announced a comprehensive €3 billion investment plan designed to strengthen Europe\'s clean energy manufacturing base. The plan targets solar panel production, battery manufacturing, and electrolyzer capacity.',
    inclusionReason: 'Directly impacts EcoSolutions\' manufacturing strategy and market opportunity.',
    linkedReportIds: ['th-10'],
    scoreBreakdown: { relevance: 0.94, llm: 0.90, freshness: 0.96, sourceAuthority: 0.88 },
  },
};

export interface ContentFilters {
  status?: ContentStatus;
  type?: ContentType;
  source?: string;
  minScore?: number;
  dateFrom?: string;
  dateTo?: string;
}

export async function listContent(workspaceId: string, filters?: ContentFilters): Promise<ContentItem[]> {
  await delay(randomBetween(300, 800));
  let items = MOCK_CONTENT[workspaceId] ? [...MOCK_CONTENT[workspaceId]] : [];
  if (filters) {
    if (filters.status) items = items.filter(i => i.status === filters.status);
    if (filters.type) items = items.filter(i => i.type === filters.type);
    if (filters.source) items = items.filter(i => i.source.toLowerCase().includes(filters.source!.toLowerCase()));
    if (filters.minScore !== undefined) items = items.filter(i => i.finalScore >= filters.minScore!);
    if (filters.dateFrom) items = items.filter(i => i.publishedAt >= filters.dateFrom!);
    if (filters.dateTo) items = items.filter(i => i.publishedAt <= filters.dateTo!);
  }
  return items;
}

export async function getContentDetail(workspaceId: string, contentId: string): Promise<ContentItemDetail | undefined> {
  await delay(randomBetween(400, 700));
  const detail = MOCK_CONTENT_DETAILS[contentId];
  if (detail) return detail;
  // Fallback: convert from content item
  const item = MOCK_CONTENT[workspaceId]?.find(i => i.id === contentId);
  if (!item) return undefined;

  // Find cluster siblings
  const clusterItems = item.clusterId
    ? MOCK_CONTENT[workspaceId]?.filter(
        i => i.clusterId === item.clusterId && i.id !== item.id,
      ) || []
    : [];

  return {
    ...item,
    body: item.body || item.snippet,
    scoreBreakdown: {
      relevance: item.relevanceScore,
      llm: item.llmScore,
      freshness: 0.85,
      sourceAuthority: 0.80,
    },
    clusterItems: clusterItems.length > 0 ? clusterItems : undefined,
  };
}

export async function getContentItemsByIds(ids: string[]): Promise<ContentItem[]> {
  await delay(randomBetween(100, 250));
  const results: ContentItem[] = [];
  const foundIds = new Set<string>();

  for (const wsId in MOCK_CONTENT) {
    for (const item of MOCK_CONTENT[wsId]) {
      if (ids.includes(item.id) && !foundIds.has(item.id)) {
        results.push(item);
        foundIds.add(item.id);
      }
    }
  }

  for (const id of ids) {
    if (!foundIds.has(id)) {
      results.push({
        id,
        workspaceId: 'unknown',
        title: `Source ${id}`,
        source: 'Monitoring Feed',
        sourceUrl: '',
        publishedAt: new Date().toISOString(),
        type: 'article',
        relevanceScore: 0.75,
        llmScore: 0.70,
        finalScore: 0.73,
        status: 'included',
        snippet: 'Content details are available in the full monitoring feed. This preview shows limited information.',
      });
    }
  }

  return results;
}
