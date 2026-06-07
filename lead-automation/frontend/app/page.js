"use client"; // this component runs in the browser so it can fetch + use state

import { useEffect, useState } from "react";

const API = "http://localhost:8000"; // the Python backend

export default function Home() {
  const [leads, setLeads] = useState([]);   // all leads from the backend
  const [filter, setFilter] = useState("All"); // current dropdown choice

  // Load all leads from the backend once, when the page first opens.
  function loadLeads() {
    fetch(`${API}/leads`)
      .then((res) => res.json())
      .then((data) => setLeads(data))
      .catch(() => setLeads([]));
  }
  useEffect(loadLeads, []);

  // Tell the backend a lead was contacted, then refresh the table.
  function markContacted(id) {
    fetch(`${API}/leads/${id}/contacted`, { method: "POST" }).then(loadLeads);
  }

  // Show all leads, or only the ones matching the selected classification.
  const visible =
    filter === "All" ? leads : leads.filter((l) => l.classification === filter);

  return (
    <main>
      <h1>Leads</h1>

      <select value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option>All</option>
        <option>Hot</option>
        <option>Warm</option>
        <option>Cold</option>
      </select>

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Source</th>
            <th>Message</th>
            <th>Classification</th>
            <th>Suggested Reply</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((lead) => (
            <tr key={lead.id}>
              <td>{lead.name}</td>
              <td>{lead.email}</td>
              <td>{lead.phone}</td>
              <td>{lead.source}</td>
              {/* truncate long messages to keep the table readable */}
              <td>{lead.message.slice(0, 60)}{lead.message.length > 60 ? "…" : ""}</td>
              <td>
                <span className={`badge ${lead.classification}`}>
                  {lead.classification}
                </span>
              </td>
              <td>{lead.suggested_reply}</td>
              <td>
                {lead.status === "Contacted" ? (
                  <span>✓ Contacted</span>
                ) : (
                  <button onClick={() => markContacted(lead.id)}>
                    Mark as Contacted
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
