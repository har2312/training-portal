import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, TopicBadge, StatusBadge, PillTabs } from "../shared/ui";

// Assigned workshops categorized strictly into Upcoming / Ongoing / Completed,
// filterable by Topic.
//   Completed  -> real finished trainings (TrainingHistory, matches Analytics total)
//   Upcoming   -> assigned future workshops (live allotments)
//   Ongoing    -> assigned in-progress workshops (live allotments)
const SCHEDULES = ["Upcoming", "Ongoing", "Completed"];

export default function MyTrainings({ personnelId }) {
  const [allotments, setAllotments] = useState([]);
  const [history, setHistory] = useState([]);
  const [topics, setTopics] = useState(["All"]);
  const [topic, setTopic] = useState("All");
  const [schedule, setSchedule] = useState("Upcoming");

  useEffect(() => {
    api.getMyAllotments(personnelId).then(setAllotments).catch(console.error);
    api.getMyAnalytics(personnelId).then((a) => setHistory(a.history)).catch(console.error);
  }, [personnelId]);
  useEffect(() => { api.getMeta().then((m) => setTopics(["All", ...m.topics])).catch(console.error); }, []);

  // Normalize both sources into one card shape.
  let items;
  if (schedule === "Completed") {
    items = history.map((h, i) => ({
      key: `h${i}`, title: h.title, topic: h.topic,
      sub: `Completed on ${h.completed_date}`, status: "Completed",
    }));
  } else {
    items = allotments
      .filter((a) => a.status !== "Rejected" && a.schedule_status === schedule)
      .map((a) => ({
        key: `a${a.allotment_id}`, title: a.title, topic: a.topic,
        sub: `${a.venue} · ${a.from_date} → ${a.to_date}`, status: a.status,
      }));
  }
  const visible = items.filter((it) => topic === "All" || it.topic === topic);

  return (
    <Card
      title="My Trainings"
      action={<PillTabs options={topics} value={topic} onChange={setTopic} />}
    >
      <div className="mb-4"><PillTabs options={SCHEDULES} value={schedule} onChange={setSchedule} /></div>
      <div className="space-y-2">
        {visible.map((it) => (
          <div key={it.key} className="flex items-center justify-between border border-slate-200 rounded-lg p-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium text-slate-800">{it.title}</p>
                <TopicBadge topic={it.topic} />
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{it.sub}</p>
            </div>
            <StatusBadge status={it.status} />
          </div>
        ))}
        {visible.length === 0 && (
          <p className="text-sm text-slate-500 py-4">No {schedule.toLowerCase()} trainings{topic !== "All" ? ` in ${topic}` : ""}.</p>
        )}
      </div>
    </Card>
  );
}
