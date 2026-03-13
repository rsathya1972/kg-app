export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  environment: string;
  db_status: string;
  message: string | null;
}
