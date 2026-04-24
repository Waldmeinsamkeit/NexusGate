/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * All real types are now defined in services/api.ts alongside the fetch functions.
 * This file re-exports them for backward compatibility.
 */

export type {
  HealthResponse,
  AdminConfig,
  MemoryRecord,
  TraceRecord,
  TestResult,
} from './services/api';
