export interface MemoryFact {
  id: number
  fact: string
  created_at: string
}

export interface ContactMemory {
  contact_id: number
  contact_name: string
  facts: MemoryFact[]
}

export interface MemoryData {
  general_facts: MemoryFact[]
  contacts: ContactMemory[]
}