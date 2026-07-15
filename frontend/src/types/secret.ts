export interface SecretSummary {
  id: string;
  name: string;
  category_id: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  created_by_id: string;
}

export interface Category {
  id: string;
  name: string;
  description: string;
  created_at: string;
}
