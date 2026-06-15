import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Stress Test Options
export const options = {
  stages: [
    { duration: '30s', target: 20 }, // Ramp up to 20 users
    { duration: '1m', target: 20 },  // Stay at 20 users
    { duration: '30s', target: 50 }, // Ramp up to 50 users (Stress)
    { duration: '1m', target: 50 },  // Stay at 50 users
    { duration: '30s', target: 0 },  // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate should be less than 1%
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // 1. Prepare a bulk request with 5 items
  const items = [];
  for (let i = 0; i < 5; i++) {
    items.push({
      user_id: `stress_user_${Math.floor(Math.random() * 10000)}`,
      data: {
        name: `Stress Test Customer ${i}`,
        amount: Math.random() * 1000,
        date: '2026-06-15'
      }
    });
  }

  const payload = JSON.stringify({
    idempotency_key: uuidv4(),
    items: items
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  // 2. Submit the job
  const res = http.post(`${BASE_URL}/jobs`, payload, params);

  // 3. Validate response
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has job_id': (r) => r.json().job_id !== undefined,
  });

  // 4. Think time between requests
  sleep(1);
}
