import type { components, paths } from "./schema";

export type ApiPaths = paths;
export type ApiSchemas = components["schemas"];
export type LenderProfile = ApiSchemas["LenderProfile"];
export type Borrower = ApiSchemas["Borrower"];
export type Invitation = ApiSchemas["Invitation"];
export type PublicInvitation = ApiSchemas["PublicInvitation"];
export type LoanApplication = ApiSchemas["LoanApplication"];
export type Loan = ApiSchemas["Loan"];
export type Installment = ApiSchemas["Installment"];
export type Repayment = ApiSchemas["Repayment"];
export type RegisterPayload = Omit<ApiSchemas["Register"], "id" | "role">;
export type LoginPayload = Pick<ApiSchemas["TokenObtainPair"], "username" | "password">;
export type LoanDecisionPayload = ApiSchemas["LoanDecision"];
export type LoanStatus = ApiSchemas["LoanStatusEnum"];
export type ApplicationStatus = ApiSchemas["LoanApplicationStatusEnum"];
export type InvitationStatus = ApiSchemas["InvitationStatusEnum"];
export type InstallmentStatus = ApiSchemas["InstallmentStatusEnum"];

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
