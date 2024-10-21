import { AgentState } from './types';

export async function getUpcomingHolidays() {
  return [
    { date: '2024-11-28', holiday: 'Thanksgiving Break' },
    { date: '2024-11-29', holiday: 'Thanksgiving Break (Day 2)' },
  ];
}

export const EXAMPLE_EVENTS = [
  {
    event: 'Freshman Fall Concert',
    activity: 'Choir',
    location: 'School Auditorium',
    startTime: '2024-11-12T19:00',
    endTime: '2023-11-12T20:30',
    grades: [9],
  },
  {
    event: 'Fall Pep Rally',
    location: 'Football Field',
    startTime: '2024-10-27T14:00',
    endTime: '2024-10-27T15:30',
    grades: [9, 10, 11, 12],
  },
  {
    event: 'Junior Fall Concert',
    activity: 'Choir',
    location: 'School Auditorium',
    startTime: '2024-11-15T19:00',
    endTime: '2024-11-15T20:30',
    grades: [11],
  },
  {
    event: 'Varsity Chess Club Tournament',
    activity: 'Chess Club',
    location: 'Library',
    startTime: '2024-11-04T16:00',
    endTime: '2024-11-04T18:00',
    grades: [11, 12],
  },
  {
    event: 'Drama Club Auditions',
    activity: 'Drama Club',
    location: 'School Auditorium',
    startTime: '2024-10-20T15:00',
    endTime: '2024-10-20T17:00',
    grades: [9, 10, 11, 12],
  },
];

export function userContext(state: AgentState) {
  return `=== User Context

- The current parent user is '${state?.parentName}'
- The current date and time is: ${new Date().toString()}

=== Registered students of the current user

${JSON.stringify(state?.students)}`;
}
