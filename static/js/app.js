let currentNote = null;
let notes = [];

const noteList = document.getElementById('noteList');
const editor = document.getElementById('editor');
const editorPlaceholder = document.getElementById('editorPlaceholder');
const noteTitle = document.getElementById('noteTitle');
const noteContent = document.getElementById('noteContent');
const syncStatus = document.getElementById('syncStatus');
const wordCount = document.getElementById('wordCount');

// Initialize
async function init() {
    await fetchNotes();
    setupEventListeners();
}

async function fetchNotes() {
    try {
        const response = await fetch('/api/notes');
        notes = await response.json();
        renderNoteList();
    } catch (error) {
        console.error('Error fetching notes:', error);
    }
}

function renderNoteList() {
    noteList.innerHTML = '';
    notes.forEach(note => {
        const div = document.createElement('div');
        div.className = `note-item ${currentNote && currentNote.id === note.id ? 'active' : ''}`;
        div.innerHTML = `
            <h3>${note.title}</h3>
            <p>${note.content.substring(0, 40)}${note.content.length > 40 ? '...' : ''}</p>
        `;
        div.onclick = () => selectNote(note);
        noteList.appendChild(div);
    });
}

function selectNote(note) {
    currentNote = note;
    editorPlaceholder.style.display = 'none';
    editor.style.display = 'flex';
    noteTitle.value = note.title;
    noteContent.value = note.content;
    updateWordCount();
    updateSyncStatus(note.is_synced);
    renderNoteList();
}

async function saveNote() {
    if (!currentNote) return;

    const updatedData = {
        title: noteTitle.value,
        content: noteContent.value
    };

    try {
        const response = await fetch(`/api/notes/${currentNote.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData)
        });
        const savedNote = await response.json();

        // Update local state
        const index = notes.findIndex(n => n.id === savedNote.id);
        notes[index] = savedNote;
        currentNote = savedNote;

        renderNoteList();
        updateSyncStatus(false); // Marked as unsynced in local DB until cloud sync
    } catch (error) {
        console.error('Error saving note:', error);
    }
}

async function createNote() {
    try {
        const response = await fetch('/api/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Note', content: '' })
        });
        const newNote = await response.json();
        notes.unshift(newNote);
        selectNote(newNote);
    } catch (error) {
        console.error('Error creating note:', error);
    }
}

async function deleteNote() {
    if (!currentNote || !confirm('Are you sure you want to delete this note?')) return;

    try {
        await fetch(`/api/notes/${currentNote.id}`, { method: 'DELETE' });
        notes = notes.filter(n => n.id !== currentNote.id);
        currentNote = null;
        editor.style.display = 'none';
        editorPlaceholder.style.display = 'flex';
        renderNoteList();
    } catch (error) {
        console.error('Error deleting note:', error);
    }
}

async function triggerSync() {
    syncStatus.innerHTML = '<i data-lucide="loader" class="animate-spin"></i> Syncing...';
    lucide.createIcons();

    try {
        const response = await fetch('/api/sync', { method: 'POST' });
        const result = await response.json();
        if (result.success) {
            await fetchNotes(); // Refresh to get updated sync status
            updateSyncStatus(true);
        } else {
            alert('Sync failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Sync error:', error);
        alert('Sync failed. Please check your connection and Supabase configuration.');
    }
}

function updateSyncStatus(isSynced) {
    if (isSynced) {
        syncStatus.className = 'sync-status synced';
        syncStatus.innerHTML = '● Synced to cloud';
    } else {
        syncStatus.className = 'sync-status unsynced';
        syncStatus.innerHTML = '● Local changes (Not Synced)';
    }
}

function updateWordCount() {
    const text = noteContent.value.trim();
    const count = text ? text.split(/\s+/).length : 0;
    wordCount.textContent = `${count} word${count !== 1 ? 's' : ''}`;
}

function setupEventListeners() {
    document.getElementById('addNoteBtn').onclick = createNote;
    document.getElementById('saveBtn').onclick = saveNote;
    document.getElementById('deleteBtn').onclick = deleteNote;
    document.getElementById('syncBtn').onclick = triggerSync;

    noteTitle.oninput = () => updateSyncStatus(false);
    noteContent.oninput = () => {
        updateWordCount();
        updateSyncStatus(false);
    };
}

init();
