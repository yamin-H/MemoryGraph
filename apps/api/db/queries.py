"""OpenCypher queries for MemoryGraph.

All queries follow HydraDB constraints:
- MERGE requires relationship pattern with two distinct nodes
- Node id property must be integer
- No MERGE followed by SET clause
- Use MATCH + SET for updates
"""

# =============================================================================
# 1. WRITE QUERIES
# =============================================================================

# -----------------------------------------------------------------------------
# Node Creation
# -----------------------------------------------------------------------------

# Create a Session node
# Requires an anchor node to satisfy HydraDB's two-node MERGE requirement
CREATE_SESSION = """
MERGE (s:Session {id: $session_id, user_id: $user_id, started_at: $started_at, status: $status})-[:SESSION_ANCHOR]->(sa:SessionAnchor {id: $anchor_id})
"""

# Create a Message node
# Linked to an anchor to satisfy MERGE constraint
CREATE_MESSAGE = """
MERGE (m:Message {id: $message_id, role: $role, content: $content, created_at: $created_at})-[:MESSAGE_ANCHOR]->(ma:MessageAnchor {id: $anchor_id})
"""

# Create a Summary node
# Contains condensed session information
CREATE_SUMMARY = """
MERGE (sum:Summary {id: $summary_id, content: $content, created_at: $created_at, token_count: $token_count})-[:SUMMARY_ANCHOR]->(sma:SummaryAnchor {id: $anchor_id})
"""

# Create a Fact node
# Represents a piece of information extracted from conversation
CREATE_FACT = """
MERGE (f:Fact {id: $fact_id, content: $content, confidence: $confidence, is_current: $is_current, created_at: $created_at})-[:FACT_ANCHOR]->(fa:FactAnchor {id: $anchor_id})
"""

# Create an Entity node
# Represents a person, place, thing, or concept mentioned in facts
CREATE_ENTITY = """
MERGE (e:Entity {id: $entity_id, name: $name, type: $entity_type})-[:ENTITY_ANCHOR]->(ea:EntityAnchor {id: $anchor_id})
"""

# -----------------------------------------------------------------------------
# Edge Creation (all use MATCH + CREATE for relationships)
# -----------------------------------------------------------------------------

# Link Session to Message
CREATE_SESSION_CONTAINS_MESSAGE = """
MATCH (s:Session {id: $session_id}), (m:Message {id: $message_id})
CREATE (s)-[:CONTAINS]->(m)
"""

# Link Session to Summary
CREATE_SESSION_HAS_SUMMARY = """
MATCH (s:Session {id: $session_id}), (sum:Summary {id: $summary_id})
CREATE (s)-[:HAS_SUMMARY]->(sum)
"""

# Link Message to Fact (message asserts this fact)
CREATE_MESSAGE_ASSERTS_FACT = """
MATCH (m:Message {id: $message_id}), (f:Fact {id: $fact_id})
CREATE (m)-[:ASSERTS]->(f)
"""

# Link Fact to Entity (fact mentions this entity)
CREATE_FACT_MENTIONS_ENTITY = """
MATCH (f:Fact {id: $fact_id}), (e:Entity {id: $entity_id})
CREATE (f)-[:MENTIONS]->(e)
"""

# Link Fact to Session (fact occurred in this session)
CREATE_FACT_OCCURRED_IN_SESSION = """
MATCH (f:Fact {id: $fact_id}), (s:Session {id: $session_id})
CREATE (f)-[:OCCURRED_IN]->(s)
"""

# Link Fact to Fact (newer fact supersedes older fact)
CREATE_FACT_SUPERSEDES_FACT = """
MATCH (f_new:Fact {id: $new_fact_id}), (f_old:Fact {id: $old_fact_id})
CREATE (f_new)-[:SUPERSEDES]->(f_old)
"""

# Link Fact to Session with invalidation reason
# Records why a fact was invalidated during this session
CREATE_FACT_INVALIDATED_BY_SESSION = """
MATCH (f:Fact {id: $fact_id}), (s:Session {id: $session_id})
CREATE (f)-[:INVALIDATED_BY {reason: $reason}]->(s)
"""

# =============================================================================
# 2. READ QUERIES
# =============================================================================

# Get a session by ID with all its messages
GET_SESSION_BY_ID = """
MATCH (s:Session {id: $session_id})-[:CONTAINS]->(m:Message)
RETURN s.id, s.user_id, s.started_at, s.status,
       collect(m.id, m.role, m.content, m.created_at) as messages
"""

# Get all facts for an entity (regardless of currency)
GET_FACTS_FOR_ENTITY = """
MATCH (f:Fact)-[:MENTIONS]->(e:Entity {id: $entity_id})
RETURN f.id, f.content, f.confidence, f.is_current, f.created_at
ORDER BY f.created_at DESC
"""

# Get only current facts for an entity (is_current: true)
GET_CURRENT_FACTS_FOR_ENTITY = """
MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e:Entity {id: $entity_id})
RETURN f.id, f.content, f.confidence, f.created_at
ORDER BY f.created_at DESC
"""

# Get session summary
GET_SESSION_SUMMARY = """
MATCH (s:Session {id: $session_id})-[:HAS_SUMMARY]->(sum:Summary)
RETURN sum.id, sum.content, sum.created_at, sum.token_count
"""

# Get all messages for a session
GET_SESSION_MESSAGES = """
MATCH (s:Session {id: $session_id})-[:CONTAINS]->(m:Message)
RETURN m.id, m.role, m.content, m.created_at
ORDER BY m.created_at ASC
"""

# =============================================================================
# 3. TRAVERSAL QUERIES
# =============================================================================

# Get full fact history for an entity (following SUPERSEDES chain)
# Returns facts from newest to oldest along the supersede chain
GET_FACT_HISTORY_FOR_ENTITY = """
MATCH (f:Fact)-[:MENTIONS]->(e:Entity {id: $entity_id})
MATCH path = (f)-[:SUPERSEDES*0..]->(older:Fact)
RETURN f.id as fact_id, f.content, f.is_current,
       older.id as superseded_id, older.content as superseded_content
ORDER BY f.created_at DESC
"""

# Get all facts across sessions for a user
# Traverses from user's sessions to facts via OCCURRED_IN
GET_ALL_FACTS_FOR_USER = """
MATCH (s:Session {user_id: $user_id})<-[:OCCURRED_IN]-(f:Fact)
RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, s.id as session_id
ORDER BY f.created_at DESC
"""

# Find conflicting facts (same entity, no SUPERSEDES link between them)
# Returns pairs of facts that mention the same entity but aren't connected
FIND_CONFLICTING_FACTS = """
MATCH (f1:Fact)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(f2:Fact)
WHERE f1.id < f2.id
  AND NOT (f1)-[:SUPERSEDES]->(f2)
  AND NOT (f2)-[:SUPERSEDES]->(f1)
  AND f1.is_current = true
  AND f2.is_current = true
RETURN e.id as entity_id, e.name as entity_name,
       f1.id as fact1_id, f1.content as fact1_content,
       f2.id as fact2_id, f2.content as fact2_content
"""

# Get facts that were invalidated
# Returns facts with their invalidation reason and session
GET_INVALIDATED_FACTS = """
MATCH (f:Fact)-[r:INVALIDATED_BY]->(s:Session)
RETURN f.id, f.content, r.reason, s.id as session_id, s.user_id
ORDER BY r.reason
"""

# Get the supersede chain for a specific fact
GET_SUPERSEDE_CHAIN = """
MATCH path = (f:Fact {id: $fact_id})-[:SUPERSEDES*0..]->(older:Fact)
RETURN older.id, older.content, older.is_current, older.created_at
ORDER BY older.created_at DESC
"""

# Find orphan facts (not linked to any session)
FIND_ORPHAN_FACTS = """
MATCH (f:Fact)
WHERE NOT (f)-[:OCCURRED_IN]->(orphan_sess:Session)
RETURN f.id, f.content, f.created_at
"""

# Get entity with fact count
GET_ENTITIES_WITH_FACT_COUNT = """
MATCH (e:Entity)<-[:MENTIONS]-(f:Fact)
RETURN e.id, e.name, e.type, count(f) as fact_count
ORDER BY fact_count DESC
"""
