// Limit simultaneous large GIF transfers, including HTTP/2 multiplexed requests.
type Job = {
  image: HTMLImageElement;
  url: string;
  ready: () => void;
  started: boolean;
  done: boolean;
  priority: number;
  timer?: ReturnType<typeof setTimeout>;
};
const queue: Job[] = [];
let active = 0;
function pump() {
  while (active < 3 && queue.length) {
    const job = queue.shift()!;
    if (job.done) continue;
    job.started = true;
    active++;
    const finish = (ok: boolean) => {
      if (job.done) return;
      job.done = true;
      clearTimeout(job.timer);
      job.image.onload = job.image.onerror = null;
      active--;
      if (ok) job.ready();
      else job.image.src = "";
      pump();
    };
    job.image.onload = () => finish(true);
    job.image.onerror = () => finish(false);
    job.timer = setTimeout(() => finish(false), 45_000);
    job.image.src = job.url;
  }
}
export function previewTransfer(url: string, ready: () => void, priority = 0) {
  const job: Job = {
    image: new Image(),
    url,
    ready,
    started: false,
    done: false,
    priority,
  };
  queue.push(job);
  queue.sort((a, b) => a.priority - b.priority);
  pump();
  return () => {
    if (job.done) return;
    job.done = true;
    clearTimeout(job.timer);
    job.image.onload = job.image.onerror = null;
    if (job.started) {
      active--;
      job.image.src = "";
    } else {
      const index = queue.indexOf(job);
      if (index >= 0) queue.splice(index, 1);
    }
    pump();
  };
}
