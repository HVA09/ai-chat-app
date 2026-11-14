/**
 * Run authenticated startup reads one at a time.
 *
 * The API's free-tier SQLAlchemy pool is intentionally small. Sequential
 * hydration avoids launching every sidebar/account collection simultaneously
 * when a session is restored after a cold start.
 */
export async function runSequentially(tasks, shouldContinue = () => true) {
  for (const task of tasks) {
    if (!shouldContinue()) return;
    await task();
  }
}
