"use strict";

const personForm = document.querySelector("#person-form");
const nameInput = document.querySelector("#name");
const emailInput = document.querySelector("#email");
const submitButton = document.querySelector("#submit-button");
const formMessage = document.querySelector("#form-message");
const statusMessage = document.querySelector("#status-message");
const peopleBody = document.querySelector("#people-body");
const peopleCount = document.querySelector("#people-count");

function showMessage(element, message, kind = "") {
  element.textContent = message;
  element.classList.remove("error", "success");
  if (kind) element.classList.add(kind);
}

function apiErrorMessage(payload, fallback) {
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => {
      const field = item.loc?.filter((part) => part !== "body").join(".");
      return `${field ? `${field}: ` : ""}${item.msg}`;
    }).join("; ");
  }
  return typeof payload?.detail === "string" ? payload.detail : fallback;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch (_error) {
      // The server may return an empty or non-JSON error response.
    }
    throw new Error(apiErrorMessage(payload, `Request failed (${response.status}).`));
  }

  if (response.status === 204) return null;
  return response.json();
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function tableMessage(message) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 4;
  cell.className = "table-message";
  cell.textContent = message;
  row.append(cell);
  peopleBody.replaceChildren(row);
}

function makeCell(text, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = text;
  return cell;
}

function renderPeople(people) {
  peopleCount.textContent = `${people.length} ${people.length === 1 ? "record" : "records"}`;
  if (people.length === 0) {
    tableMessage("No people yet. Add your first person using the form above.");
    return;
  }

  const rows = people.map((person) => {
    const row = document.createElement("tr");
    row.append(makeCell(person.name));
    row.append(makeCell(person.email, "email-cell"));
    row.append(makeCell(formatDate(person.created_at)));

    const actionCell = document.createElement("td");
    actionCell.className = "action-cell";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "button button-delete";
    deleteButton.textContent = "Delete";
    deleteButton.setAttribute("aria-label", `Delete ${person.name}`);
    deleteButton.addEventListener("click", () => deletePerson(person, deleteButton));
    actionCell.append(deleteButton);
    row.append(actionCell);
    return row;
  });
  peopleBody.replaceChildren(...rows);
}

async function loadPeople({ announceLoading = true } = {}) {
  if (announceLoading) showMessage(statusMessage, "Loading people…");
  tableMessage("Loading people…");
  try {
    const people = await requestJson("/api/people");
    renderPeople(people);
    if (announceLoading) {
      showMessage(statusMessage, people.length ? "People loaded." : "Your directory is empty.");
    }
    return true;
  } catch (error) {
    peopleCount.textContent = "— records";
    tableMessage("People could not be loaded.");
    showMessage(statusMessage, error.message || "Could not connect to the API.", "error");
    return false;
  }
}

personForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(formMessage, "");

  const name = nameInput.value.trim();
  const email = emailInput.value.trim();
  if (!name) {
    showMessage(formMessage, "Enter a name.", "error");
    nameInput.focus();
    return;
  }
  if (!emailInput.validity.valid || !email) {
    showMessage(formMessage, "Enter a valid email address.", "error");
    emailInput.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Adding…";
  try {
    await requestJson("/api/people", {
      method: "POST",
      body: JSON.stringify({ name, email }),
    });
    personForm.reset();
    showMessage(formMessage, "Person added successfully.", "success");
    await loadPeople({ announceLoading: false });
    nameInput.focus();
  } catch (error) {
    showMessage(formMessage, error.message || "The person could not be added.", "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Add person";
  }
});

async function deletePerson(person, button) {
  if (!window.confirm(`Delete ${person.name}? This cannot be undone.`)) return;
  button.disabled = true;
  button.textContent = "Deleting…";
  showMessage(statusMessage, `Deleting ${person.name}…`);
  try {
    await requestJson(`/api/people/${person.id}`, { method: "DELETE" });
    const refreshed = await loadPeople({ announceLoading: false });
    if (refreshed) {
      showMessage(statusMessage, `${person.name} was deleted.`, "success");
    } else {
      showMessage(statusMessage, `${person.name} was deleted, but the list could not be refreshed.`, "error");
    }
  } catch (error) {
    button.disabled = false;
    button.textContent = "Delete";
    showMessage(statusMessage, error.message || "The person could not be deleted.", "error");
  }
}

loadPeople();
