import React, { useState, useEffect } from 'react';
import { api } from './api';
import { User, Project, SourceVideo, Clip, DashboardStats, TemplatePreset } from './types';

import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ClipsExplorer } from './components/ClipsExplorer';
import { ClipEditor } from './components/ClipEditor';
import { ExportCenter } from './components/ExportCenter';
import { BrandTemplatesView } from './components/BrandTemplatesView';
import { ProjectsView } from './components/ProjectsView';
import { SettingsView } from './components/SettingsView';
import { ProcessingView } from './components/ProcessingView';
import { UploadModal } from './components/UploadModal';
import { AuthModal } from './components/AuthModal';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<SourceVideo[]>([]);
  const [activeVideo, setActiveVideo] = useState<SourceVideo | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
  const [templates, setTemplates] = useState<TemplatePreset[]>([]);

  const [activeView, setActiveView] = useState<string>('dashboard');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [processingVideoId, setProcessingVideoId] = useState<string | null>(null);

  // Initial data loading
  useEffect(() => {
    loadUserData();
    loadTemplates();
  }, []);

  const loadUserData = async () => {
    try {
      const me = await api.getMe();
      setUser(me);
      await refreshData();
    } catch (e) {
      console.log('Unauthenticated or using demo mode');
      // If token expired, try logging in with demo account
      try {
        const res = await api.login({ email: 'creator@opusclip.pro', password: 'password123' });
        setUser(res.user);
        await refreshData();
      } catch (err) {
        setIsAuthOpen(true);
      }
    }
  };

  const refreshData = async () => {
    try {
      const [projData, statsData, vidsData] = await Promise.all([
        api.getProjects(),
        api.getStats(),
        api.getVideos()
      ]);
      setProjects(projData);
      if (projData.length > 0 && !currentProject) {
        setCurrentProject(projData[0]);
      }
      setStats(statsData);
      setVideos(vidsData);
    } catch (err) {
      console.error('Failed refreshing data:', err);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
    } catch (err) {
      console.error(err);
    }
  };

  // Video selection
  const handleSelectVideo = async (vid: SourceVideo) => {
    setActiveVideo(vid);
    if (vid.status !== 'completed' && vid.status !== 'failed') {
      setProcessingVideoId(vid.id);
      setActiveView('processing');
    } else {
      try {
        const clipData = await api.getClips(vid.id);
        setClips(clipData);
        setActiveView('clips');
      } catch (err) {
        console.error(err);
      }
    }
  };

  // Upload completed callback
  const handleUploadSuccess = (vid: SourceVideo) => {
    setVideos((prev) => [vid, ...prev]);
    setActiveVideo(vid);
    setProcessingVideoId(vid.id);
    setActiveView('processing');
  };

  // Processing completed callback
  const handleProcessingComplete = async (vid: SourceVideo) => {
    setActiveVideo(vid);
    const clipData = await api.getClips(vid.id);
    setClips(clipData);
    setProcessingVideoId(null);
    setActiveView('clips');
    refreshData();
  };

  const handleSelectClip = (clip: Clip) => {
    setSelectedClip(clip);
    setActiveView('editor');
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setIsAuthOpen(true);
  };

  return (
    <div className="min-h-screen bg-dark-950 flex flex-col text-gray-100">
      {/* Top Navigation */}
      <Navbar
        user={user}
        onOpenUpload={() => setIsUploadOpen(true)}
        onLogout={handleLogout}
        onOpenAuth={() => setIsAuthOpen(true)}
        activeView={activeView}
        setActiveView={setActiveView}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          selectedClipId={selectedClip?.id || null}
        />

        {/* Main Content Viewport */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            {activeView === 'dashboard' && (
              <DashboardView
                stats={stats}
                videos={videos}
                onOpenUpload={() => setIsUploadOpen(true)}
                onSelectVideo={handleSelectVideo}
                onRefresh={refreshData}
              />
            )}

            {activeView === 'processing' && processingVideoId && (
              <ProcessingView
                videoId={processingVideoId}
                onCompleted={handleProcessingComplete}
                onCancel={() => setActiveView('dashboard')}
              />
            )}

            {activeView === 'clips' && activeVideo && (
              <ClipsExplorer
                video={activeVideo}
                clips={clips}
                onSelectClip={handleSelectClip}
                onRefreshClips={() => activeVideo && handleSelectVideo(activeVideo)}
              />
            )}

            {activeView === 'editor' && selectedClip && (
              <ClipEditor
                clip={selectedClip}
                onClipUpdated={(updated) => {
                  setSelectedClip(updated);
                  setClips((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
                }}
                onBack={() => setActiveView('clips')}
                onGoToExport={() => setActiveView('exports')}
              />
            )}

            {activeView === 'exports' && (
              <ExportCenter
                clips={clips}
                onRefresh={() => activeVideo && handleSelectVideo(activeVideo)}
                onOpenEditor={handleSelectClip}
              />
            )}

            {activeView === 'templates' && (
              <BrandTemplatesView templates={templates} />
            )}

            {activeView === 'projects' && (
              <ProjectsView
                projects={projects}
                onSelectProject={(p) => {
                  setCurrentProject(p);
                  setActiveView('dashboard');
                }}
                onRefresh={refreshData}
              />
            )}

            {activeView === 'settings' && (
              <SettingsView user={user} />
            )}
          </div>
        </main>
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        projects={projects}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={(u) => {
          setUser(u);
          refreshData();
        }}
      />
    </div>
  );
};

export default App;
