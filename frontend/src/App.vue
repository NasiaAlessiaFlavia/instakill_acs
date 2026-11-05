<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>Instakill</h1>
      <nav v-if="user">
        <span class="user">@{{ user.username }}</span>
        <button @click="toggleAnalytics">Analytics</button>
        <button @click="logout">Logout</button>
      </nav>
    </header>

    <main class="content">
      <section v-if="!user" class="card">
        <div class="tabs">
          <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">Login</button>
          <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">Register</button>
        </div>
        <form @submit.prevent="submitAuth" class="form">
          <input v-model="authForm.usernameOrEmail" v-if="authMode === 'login'" placeholder="Username or email" required>
          <input v-model="authForm.username" v-else placeholder="Username" required minlength="3">
          <input v-model="authForm.email" v-if="authMode === 'register'" type="email" placeholder="Email" required>
          <input v-model="authForm.password" type="password" placeholder="Password" required minlength="6">
          <p v-if="error" class="error">{{ error }}</p>
          <button type="submit">Continue</button>
        </form>
      </section>

      <!-- Analytics Panel -->
      <section v-if="user && showAnalytics" class="card analytics">
        <div class="analytics-header">
          <h2>Your Analytics</h2>
          <button class="close-btn" @click="showAnalytics = false">✕</button>
        </div>

        <div v-if="analyticsLoading" class="analytics-loading">Loading…</div>
        <div v-else-if="analyticsError" class="error">{{ analyticsError }}</div>
        <div v-else-if="analytics" class="analytics-grid">

          <!-- 1. Weekly Stats -->
          <div class="analytics-card">
            <h3>Posts per Week</h3>
            <table v-if="analytics.weeklyStats.length" class="stats-table">
              <thead><tr><th>Week</th><th>Posts</th><th>Likes</th><th>Comments</th></tr></thead>
              <tbody>
                <tr v-for="w in analytics.weeklyStats" :key="w.week">
                  <td>{{ w.week }}</td>
                  <td>{{ w.posts }}</td>
                  <td>{{ w.likes }}</td>
                  <td>{{ w.comments }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="no-data">No posts yet.</p>
          </div>

          <!-- 2. Top 5 Posts -->
          <div class="analytics-card">
            <h3>Top 5 Posts by Engagement</h3>
            <ol v-if="analytics.topPosts.length" class="top-posts">
              <li v-for="p in analytics.topPosts" :key="p.postId">
                <span class="post-preview">{{ p.content }}</span>
                <span class="engagement-badge">{{ p.engagement }}</span>
              </li>
            </ol>
            <p v-else class="no-data">No posts yet.</p>
          </div>

          <!-- 3. Like-to-Comment Ratio -->
          <div class="analytics-card stat-card">
            <h3>Like / Comment Ratio</h3>
            <p class="big-stat">
              {{ analytics.likeToCommentRatio != null ? analytics.likeToCommentRatio.toFixed(2) : 'N/A' }}
            </p>
            <small>likes per comment across all your posts</small>
          </div>

          <!-- 4. Avg Likes by Media Type -->
          <div class="analytics-card">
            <h3>Avg Likes by Media Type</h3>
            <table v-if="analytics.avgLikesByMediaType.length" class="stats-table">
              <thead><tr><th>Type</th><th>Avg Likes</th></tr></thead>
              <tbody>
                <tr v-for="m in analytics.avgLikesByMediaType" :key="m.mediaType">
                  <td>{{ m.mediaType }}</td>
                  <td>{{ m.avgLikes.toFixed(1) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="no-data">No media posts yet.</p>
          </div>

          <!-- 5. Top Percentile -->
          <div class="analytics-card stat-card">
            <h3>Engagement Rank</h3>
            <p v-if="analytics.topPercentile != null" class="big-stat">
              Top {{ analytics.topPercentile }}%
            </p>
            <p v-else class="big-stat">N/A</p>
            <small>of all users by average engagement per post</small>
          </div>

        </div>
      </section>

      <section v-if="user && !showAnalytics" class="feed">
        <form @submit.prevent="createNewPost" class="card form composer">
          <textarea v-model="composer.content" rows="3" placeholder="Share something..." required></textarea>
          <input type="file" accept="image/*,video/*" @change="onFileChosen">
          <small v-if="composer.imageUrl" class="media-hint">{{ composer.imageUrl }}</small>
          <small v-if="uploadError" class="error">{{ uploadError }}</small>
          <div class="actions">
            <button type="submit">Post</button>
          </div>
        </form>

        <div class="feed-toolbar">
          <h2>Feed</h2>
          <div class="sort">
            <button :class="{ active: sort === 'new' }" @click="changeSort('new')">Newest</button>
            <button :class="{ active: sort === 'trending' }" @click="changeSort('trending')">Trending</button>
          </div>
        </div>

        <article v-for="post in posts" :key="post.id" class="card post">
          <header>
            <div>
              <h3>@{{ post.author.username }}</h3>
              <small>{{ formatDate(post.createdAt) }}</small>
            </div>
            <div class="metrics">
              <span>{{ post.likeCount }} likes</span>
              <span> | </span>
              <span>{{ post.commentCount }} comments</span>
            </div>
          </header>
          <p>{{ post.content }}</p>
          <img v-if="post.imageUrl" :src="post.imageUrl" alt="post image">

          <!-- Comments Section -->
          <section class="comments">
            <div v-if="comments[post.id] && comments[post.id].length">
              <div v-for="comment in comments[post.id]" :key="comment.id" class="comment">
                <b>@{{ comment.author.username }}</b> <small>{{ formatDate(comment.createdAt) }}</small>
                <div>{{ comment.content }}</div>
              </div>
            </div>
            <div v-else class="no-comments">
              <em>No comments yet.</em>
            </div>
            <form v-if="user" @submit.prevent="submitComment(post.id)" class="comment-form">
              <input
                v-model="newComment[post.id]"
                :placeholder="'Add a comment...'"
                required
                minlength="1"
              />
              <button type="submit" :disabled="commentLoading[post.id]">Comment</button>
            </form>
            <div v-if="commentError[post.id]" class="error">{{ commentError[post.id] }}</div>
          </section>

          <footer>
            <button @click="togglePostLike(post)">
              {{ post.likedByCurrentUser ? 'Unlike' : 'Like' }}
            </button>
          </footer>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { createPost, fetchMe, listFeed, login, register as registerUser, toggleLike, listComments, addComment, uploadMedia, fetchAnalytics } from './api'

const user = ref(null)
const posts = ref([])
const sort = ref('new')
const authMode = ref('login')
const error = ref('')
const authForm = reactive({ username: '', email: '', password: '', usernameOrEmail: '' })
const composer = reactive({ content: '', imageUrl: '' })
const uploadError = ref('')

// Comments state
const comments = reactive({})
const newComment = reactive({})
const commentLoading = reactive({})
const commentError = reactive({})

// Analytics state
const showAnalytics = ref(false)
const analytics = ref(null)
const analyticsLoading = ref(false)
const analyticsError = ref('')

onMounted(async () => {
  await bootstrap()
})

async function bootstrap() {
  try {
    user.value = await fetchMe()
    await loadFeed()
  } catch (e) {
    user.value = null
  }
}

async function submitAuth() {
  error.value = ''
  try {
    if (authMode.value === 'login') {
      const result = await login({
        usernameOrEmail: authForm.usernameOrEmail,
        password: authForm.password
      })
      user.value = result.user
    } else {
      const result = await registerUser({
        username: authForm.username,
        email: authForm.email,
        password: authForm.password
      })
      user.value = result.user
    }
    await loadFeed()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Authentication failed'
  }
}

async function loadFeed() {
  posts.value = await listFeed({ sort: sort.value })
  for (const post of posts.value) {
    await loadComments(post.id)
  }
}

async function loadComments(postId) {
  try {
    commentError[postId] = ''
    comments[postId] = await listComments(postId)
  } catch (e) {
    comments[postId] = []
    commentError[postId] = 'Failed to load comments'
  }
}

async function submitComment(postId) {
  if (!newComment[postId] || !newComment[postId].trim()) return
  commentLoading[postId] = true
  commentError[postId] = ''
  try {
    await addComment(postId, { content: newComment[postId] })
    newComment[postId] = ''
    await loadComments(postId)
    const post = posts.value.find(p => p.id === postId)
    if (post) post.commentCount = (comments[postId]?.length || 0)
  } catch (e) {
    commentError[postId] = e.response?.data?.detail || 'Failed to add comment'
  } finally {
    commentLoading[postId] = false
  }
}

async function onFileChosen(event) {
  const file = event.target.files[0]
  if (!file) return
  uploadError.value = ''
  try {
    const result = await uploadMedia(file)
    composer.imageUrl = result.mediaUrl
  } catch (e) {
    uploadError.value = 'Upload failed'
  }
}

async function createNewPost() {
  if (!composer.content.trim()) return
  await createPost({ content: composer.content, imageUrl: composer.imageUrl || null })
  composer.content = ''
  composer.imageUrl = ''
  uploadError.value = ''
  await loadFeed()
}

async function togglePostLike(post) {
  const result = await toggleLike(post.id)
  post.likedByCurrentUser = result.liked
  post.likeCount = result.likeCount
}

function changeSort(next) {
  if (sort.value === next) return
  sort.value = next
  loadFeed()
}

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

async function toggleAnalytics() {
  if (showAnalytics.value) {
    showAnalytics.value = false
    return
  }
  showAnalytics.value = true
  analyticsLoading.value = true
  analyticsError.value = ''
  try {
    analytics.value = await fetchAnalytics()
  } catch (e) {
    analyticsError.value = 'Failed to load analytics'
  } finally {
    analyticsLoading.value = false
  }
}

async function logout() {
  try {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
  } catch (e) {
    // ignore
  }
  document.cookie = 'ACCESS_TOKEN=; Max-Age=0; path=/'
  user.value = null
  posts.value = []
  showAnalytics.value = false
}
</script>

<style scoped>
.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.app-header nav {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.app-header button {
  background: #111827;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 999px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 10px 30px rgba(17, 24, 39, 0.1);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form input,
.form textarea {
  width: 100%;
  padding: 0.75rem;
  border-radius: 10px;
  border: 1px solid #d1d5db;
}

.form button {
  align-self: flex-start;
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 0.5rem 1.25rem;
  border-radius: 999px;
}

.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.tabs button {
  background: transparent;
  border: none;
  font-weight: 600;
  color: #6b7280;
}

.tabs button.active {
  color: #111827;
}

.error {
  color: #ef4444;
}

.feed-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sort button {
  margin-left: 0.5rem;
  border: none;
  background: #e5e7eb;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
}

.sort button.active {
  background: #111827;
  color: #fff;
}

.post header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.post img {
  margin-top: 0.75rem;
  width: 100%;
  border-radius: 12px;
}

.post footer {
  margin-top: 1rem;
}

.post footer button {
  background: #111827;
  border: none;
  color: #fff;
  padding: 0.4rem 1.2rem;
  border-radius: 999px;
}

.comments {
  margin-top: 1.2rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.comment {
  margin-bottom: 0.7rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #f3f4f6;
}

.no-comments {
  color: #6b7280;
  margin-bottom: 0.7rem;
}

.comment-form {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.comment-form input {
  flex: 1;
  padding: 0.5rem;
  border-radius: 8px;
  border: 1px solid #d1d5db;
}

.comment-form button {
  background: #2563eb;
  color: #fff;
  border: none;
  padding: 0.4rem 1.1rem;
  border-radius: 999px;
}

.media-hint {
  color: #6b7280;
  word-break: break-all;
}

/* ── Analytics ── */
.analytics {
  margin-bottom: 0.5rem;
}

.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.1rem;
  cursor: pointer;
  color: #6b7280;
}

.analytics-loading {
  color: #6b7280;
  padding: 1rem 0;
}

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.analytics-card {
  background: #f9fafb;
  border-radius: 12px;
  padding: 1rem;
}

.analytics-card h3 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: #374151;
}

.stat-card {
  text-align: center;
}

.big-stat {
  font-size: 2rem;
  font-weight: 700;
  color: #2563eb;
  margin: 0.5rem 0;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.stats-table th,
.stats-table td {
  text-align: left;
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.stats-table th {
  color: #6b7280;
  font-weight: 600;
}

.top-posts {
  padding-left: 1.2rem;
  margin: 0;
  font-size: 0.85rem;
}

.top-posts li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.3rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.post-preview {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #374151;
}

.engagement-badge {
  flex-shrink: 0;
  background: #dbeafe;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
}

.no-data {
  color: #9ca3af;
  font-size: 0.85rem;
}
</style>
