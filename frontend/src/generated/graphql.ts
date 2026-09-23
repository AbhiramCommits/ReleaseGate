/** Internal type. DO NOT USE DIRECTLY. */
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
/** Internal type. DO NOT USE DIRECTLY. */
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import { DocumentTypeDecoration } from '@graphql-typed-document-node/core';
import { useMutation, useQuery, UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';
import { graphqlFetcher } from 'src/api/graphqlClient';
export type ChangeRequestInput = {
  description: string;
  riskLevel: RiskLevel;
  subsystem: string;
  title: string;
  vehicleProgram: string;
};

export type ChangeRequestUpdateInput = {
  description?: string | null | undefined;
  riskLevel?: RiskLevel | null | undefined;
  subsystem?: string | null | undefined;
  title?: string | null | undefined;
  vehicleProgram?: string | null | undefined;
};

export enum ChangeStage {
  Approved = 'APPROVED',
  Draft = 'DRAFT',
  EngineeringReview = 'ENGINEERING_REVIEW',
  ManufacturingReview = 'MANUFACTURING_REVIEW',
  Rejected = 'REJECTED',
  Submitted = 'SUBMITTED'
}

export enum Decision {
  Approve = 'APPROVE',
  Reject = 'REJECT',
  RequestChanges = 'REQUEST_CHANGES'
}

export enum RiskLevel {
  High = 'HIGH',
  Low = 'LOW',
  Medium = 'MEDIUM'
}

export enum Role {
  Admin = 'ADMIN',
  Requester = 'REQUESTER',
  Reviewer = 'REVIEWER'
}

export enum WorkflowAction {
  Approve = 'APPROVE',
  Reject = 'REJECT',
  RequestChanges = 'REQUEST_CHANGES',
  Submit = 'SUBMIT'
}

export type CreateChangeRequestMutationVariables = Exact<{
  input: ChangeRequestInput;
}>;


export type CreateChangeRequestMutation = { createChangeRequest: { id: string, ticketKey: string, title: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, updatedAt: string } };

export type UpdateChangeRequestMutationVariables = Exact<{
  id: string | number;
  input: ChangeRequestUpdateInput;
}>;


export type UpdateChangeRequestMutation = { updateChangeRequest: { id: string, ticketKey: string, title: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, updatedAt: string } };

export type TransitionChangeRequestMutationVariables = Exact<{
  id: string | number;
  action: WorkflowAction;
  comment?: string | null | undefined;
}>;


export type TransitionChangeRequestMutation = { transitionChangeRequest: { id: string, ticketKey: string, title: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, updatedAt: string } };

export type ChangeRequestSummaryFragment = { id: string, ticketKey: string, title: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, updatedAt: string };

export type PageInfoFieldsFragment = { hasNextPage: boolean, hasPreviousPage: boolean, startCursor: string | null, endCursor: string | null };

export type MeQueryVariables = Exact<{ [key: string]: never; }>;


export type MeQuery = { me: { id: string, email: string, fullName: string, role: Role } };

export type ChangeRequestsQueryVariables = Exact<{
  stage?: ChangeStage | null | undefined;
  riskLevel?: RiskLevel | null | undefined;
  subsystem?: string | null | undefined;
  first?: number | null | undefined;
  after?: string | null | undefined;
}>;


export type ChangeRequestsQuery = { changeRequests: { totalCount: number, edges: Array<{ cursor: string, node: { id: string, ticketKey: string, title: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, updatedAt: string } }>, pageInfo: { hasNextPage: boolean, hasPreviousPage: boolean, startCursor: string | null, endCursor: string | null } } };

export type ChangeRequestDetailQueryVariables = Exact<{
  id: string | number;
}>;


export type ChangeRequestDetailQuery = { changeRequest: { id: string, ticketKey: string, title: string, description: string, vehicleProgram: string, subsystem: string, riskLevel: RiskLevel, currentStage: ChangeStage, requesterId: string, createdAt: string, updatedAt: string, requester: { id: string, fullName: string, email: string, role: Role }, approvals: Array<{ id: string, stage: ChangeStage, decision: Decision, comment: string | null, decidedAt: string, reviewer: { id: string, fullName: string, role: Role } }>, auditEvents: Array<{ id: string, fromStage: ChangeStage | null, toStage: ChangeStage | null, action: string, metadata: unknown, createdAt: string, actor: { id: string, fullName: string, role: Role } }> } | null };

export type CycleTimeQueryVariables = Exact<{ [key: string]: never; }>;


export type CycleTimeQuery = { cycleTimeAnalytics: { endToEndAverageHours: number | null, stageMetrics: Array<{ stage: ChangeStage, averageHours: number | null, medianHours: number | null, samples: number }>, currentStageCounts: Array<{ stage: ChangeStage, count: number }>, topSlowestStages: Array<{ stage: ChangeStage, averageHours: number | null, medianHours: number | null, samples: number }> } };


export class TypedDocumentString<TResult, TVariables>
  extends String
  implements DocumentTypeDecoration<TResult, TVariables>
{
  __apiType?: NonNullable<DocumentTypeDecoration<TResult, TVariables>['__apiType']>;
  private value: string;
  public __meta__?: Record<string, any> | undefined;

  constructor(value: string, __meta__?: Record<string, any> | undefined) {
    super(value);
    this.value = value;
    this.__meta__ = __meta__;
  }

  override toString(): string & DocumentTypeDecoration<TResult, TVariables> {
    return this.value;
  }
}
export const ChangeRequestSummaryFragmentDoc = new TypedDocumentString(`
    fragment ChangeRequestSummary on ChangeRequestType {
  id
  ticketKey
  title
  vehicleProgram
  subsystem
  riskLevel
  currentStage
  updatedAt
}
    `, {"fragmentName":"ChangeRequestSummary"});
export const PageInfoFieldsFragmentDoc = new TypedDocumentString(`
    fragment PageInfoFields on PageInfo {
  hasNextPage
  hasPreviousPage
  startCursor
  endCursor
}
    `, {"fragmentName":"PageInfoFields"});
export const CreateChangeRequestDocument = new TypedDocumentString(`
    mutation CreateChangeRequest($input: ChangeRequestInput!) {
  createChangeRequest(input: $input) {
    ...ChangeRequestSummary
  }
}
    fragment ChangeRequestSummary on ChangeRequestType {
  id
  ticketKey
  title
  vehicleProgram
  subsystem
  riskLevel
  currentStage
  updatedAt
}`);

export const useCreateChangeRequestMutation = <
      TError = Error,
      TContext = unknown
    >(options?: UseMutationOptions<CreateChangeRequestMutation, TError, CreateChangeRequestMutationVariables, TContext>) => {
    
    return useMutation<CreateChangeRequestMutation, TError, CreateChangeRequestMutationVariables, TContext>(
      {
    mutationKey: ['CreateChangeRequest'],
    mutationFn: (variables?: CreateChangeRequestMutationVariables) => graphqlFetcher<CreateChangeRequestMutation, CreateChangeRequestMutationVariables>(CreateChangeRequestDocument, variables)(),
    ...options
  }
    )};

useCreateChangeRequestMutation.getKey = () => ['CreateChangeRequest'];

export const UpdateChangeRequestDocument = new TypedDocumentString(`
    mutation UpdateChangeRequest($id: ID!, $input: ChangeRequestUpdateInput!) {
  updateChangeRequest(id: $id, input: $input) {
    ...ChangeRequestSummary
  }
}
    fragment ChangeRequestSummary on ChangeRequestType {
  id
  ticketKey
  title
  vehicleProgram
  subsystem
  riskLevel
  currentStage
  updatedAt
}`);

export const useUpdateChangeRequestMutation = <
      TError = Error,
      TContext = unknown
    >(options?: UseMutationOptions<UpdateChangeRequestMutation, TError, UpdateChangeRequestMutationVariables, TContext>) => {
    
    return useMutation<UpdateChangeRequestMutation, TError, UpdateChangeRequestMutationVariables, TContext>(
      {
    mutationKey: ['UpdateChangeRequest'],
    mutationFn: (variables?: UpdateChangeRequestMutationVariables) => graphqlFetcher<UpdateChangeRequestMutation, UpdateChangeRequestMutationVariables>(UpdateChangeRequestDocument, variables)(),
    ...options
  }
    )};

useUpdateChangeRequestMutation.getKey = () => ['UpdateChangeRequest'];

export const TransitionChangeRequestDocument = new TypedDocumentString(`
    mutation TransitionChangeRequest($id: ID!, $action: WorkflowAction!, $comment: String) {
  transitionChangeRequest(id: $id, action: $action, comment: $comment) {
    id
    ticketKey
    title
    vehicleProgram
    subsystem
    riskLevel
    currentStage
    updatedAt
  }
}
    `);

export const useTransitionChangeRequestMutation = <
      TError = Error,
      TContext = unknown
    >(options?: UseMutationOptions<TransitionChangeRequestMutation, TError, TransitionChangeRequestMutationVariables, TContext>) => {
    
    return useMutation<TransitionChangeRequestMutation, TError, TransitionChangeRequestMutationVariables, TContext>(
      {
    mutationKey: ['TransitionChangeRequest'],
    mutationFn: (variables?: TransitionChangeRequestMutationVariables) => graphqlFetcher<TransitionChangeRequestMutation, TransitionChangeRequestMutationVariables>(TransitionChangeRequestDocument, variables)(),
    ...options
  }
    )};

useTransitionChangeRequestMutation.getKey = () => ['TransitionChangeRequest'];

export const MeDocument = new TypedDocumentString(`
    query Me {
  me {
    id
    email
    fullName
    role
  }
}
    `);

export const useMeQuery = <
      TData = MeQuery,
      TError = Error
    >(
      variables?: MeQueryVariables,
      options?: Omit<UseQueryOptions<MeQuery, TError, TData>, 'queryKey'> & { queryKey?: UseQueryOptions<MeQuery, TError, TData>['queryKey'] }
    ) => {
    
    return useQuery<MeQuery, TError, TData>(
      {
    queryKey: variables === undefined ? ['Me'] : ['Me', variables],
    queryFn: graphqlFetcher<MeQuery, MeQueryVariables>(MeDocument, variables),
    ...options
  }
    )};

useMeQuery.getKey = (variables?: MeQueryVariables) => variables === undefined ? ['Me'] : ['Me', variables];

export const ChangeRequestsDocument = new TypedDocumentString(`
    query ChangeRequests($stage: ChangeStage, $riskLevel: RiskLevel, $subsystem: String, $first: Int, $after: String) {
  changeRequests(
    stage: $stage
    riskLevel: $riskLevel
    subsystem: $subsystem
    first: $first
    after: $after
  ) {
    edges {
      cursor
      node {
        ...ChangeRequestSummary
      }
    }
    pageInfo {
      ...PageInfoFields
    }
    totalCount
  }
}
    fragment ChangeRequestSummary on ChangeRequestType {
  id
  ticketKey
  title
  vehicleProgram
  subsystem
  riskLevel
  currentStage
  updatedAt
}
fragment PageInfoFields on PageInfo {
  hasNextPage
  hasPreviousPage
  startCursor
  endCursor
}`);

export const useChangeRequestsQuery = <
      TData = ChangeRequestsQuery,
      TError = Error
    >(
      variables?: ChangeRequestsQueryVariables,
      options?: Omit<UseQueryOptions<ChangeRequestsQuery, TError, TData>, 'queryKey'> & { queryKey?: UseQueryOptions<ChangeRequestsQuery, TError, TData>['queryKey'] }
    ) => {
    
    return useQuery<ChangeRequestsQuery, TError, TData>(
      {
    queryKey: variables === undefined ? ['ChangeRequests'] : ['ChangeRequests', variables],
    queryFn: graphqlFetcher<ChangeRequestsQuery, ChangeRequestsQueryVariables>(ChangeRequestsDocument, variables),
    ...options
  }
    )};

useChangeRequestsQuery.getKey = (variables?: ChangeRequestsQueryVariables) => variables === undefined ? ['ChangeRequests'] : ['ChangeRequests', variables];

export const ChangeRequestDetailDocument = new TypedDocumentString(`
    query ChangeRequestDetail($id: ID!) {
  changeRequest(id: $id) {
    id
    ticketKey
    title
    description
    vehicleProgram
    subsystem
    riskLevel
    currentStage
    requesterId
    createdAt
    updatedAt
    requester {
      id
      fullName
      email
      role
    }
    approvals {
      id
      stage
      decision
      comment
      decidedAt
      reviewer {
        id
        fullName
        role
      }
    }
    auditEvents {
      id
      fromStage
      toStage
      action
      metadata
      createdAt
      actor {
        id
        fullName
        role
      }
    }
  }
}
    `);

export const useChangeRequestDetailQuery = <
      TData = ChangeRequestDetailQuery,
      TError = Error
    >(
      variables: ChangeRequestDetailQueryVariables,
      options?: Omit<UseQueryOptions<ChangeRequestDetailQuery, TError, TData>, 'queryKey'> & { queryKey?: UseQueryOptions<ChangeRequestDetailQuery, TError, TData>['queryKey'] }
    ) => {
    
    return useQuery<ChangeRequestDetailQuery, TError, TData>(
      {
    queryKey: ['ChangeRequestDetail', variables],
    queryFn: graphqlFetcher<ChangeRequestDetailQuery, ChangeRequestDetailQueryVariables>(ChangeRequestDetailDocument, variables),
    ...options
  }
    )};

useChangeRequestDetailQuery.getKey = (variables: ChangeRequestDetailQueryVariables) => ['ChangeRequestDetail', variables];

export const CycleTimeDocument = new TypedDocumentString(`
    query CycleTime {
  cycleTimeAnalytics {
    stageMetrics {
      stage
      averageHours
      medianHours
      samples
    }
    currentStageCounts {
      stage
      count
    }
    endToEndAverageHours
    topSlowestStages {
      stage
      averageHours
      medianHours
      samples
    }
  }
}
    `);

export const useCycleTimeQuery = <
      TData = CycleTimeQuery,
      TError = Error
    >(
      variables?: CycleTimeQueryVariables,
      options?: Omit<UseQueryOptions<CycleTimeQuery, TError, TData>, 'queryKey'> & { queryKey?: UseQueryOptions<CycleTimeQuery, TError, TData>['queryKey'] }
    ) => {
    
    return useQuery<CycleTimeQuery, TError, TData>(
      {
    queryKey: variables === undefined ? ['CycleTime'] : ['CycleTime', variables],
    queryFn: graphqlFetcher<CycleTimeQuery, CycleTimeQueryVariables>(CycleTimeDocument, variables),
    ...options
  }
    )};

useCycleTimeQuery.getKey = (variables?: CycleTimeQueryVariables) => variables === undefined ? ['CycleTime'] : ['CycleTime', variables];
