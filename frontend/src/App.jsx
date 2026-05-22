import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { HomePage } from './pages/HomePage';
import { ProjectsPage } from './pages/ProjectsPage';
import { useIsLowPowerDevice } from './hooks/useIsLowPowerDevice';

const UnicornScene = lazy(() => import('unicornstudio-react'));

function StaticAuraBackground() {
  return (
    <div
      className="absolute inset-0 w-full h-full"
      style={{
        background:
          'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(249,115,22,0.18) 0%, rgba(180,60,10,0.10) 35%, rgba(10,8,15,0) 70%), radial-gradient(ellipse 60% 50% at 70% 60%, rgba(120,40,200,0.10) 0%, rgba(10,8,15,0) 70%), #0a080f',
      }}
    />
  );
}

export default function App() {
  const isLowPower = useIsLowPowerDevice();

  return (
    <div className="min-h-screen flex flex-col relative overflow-x-hidden">
      {/* Aura Background Layers */}
      <div className="fixed top-0 w-full h-screen -z-10 hue-rotate-180">
        {isLowPower ? (
          <StaticAuraBackground />
        ) : (
          <Suspense fallback={<StaticAuraBackground />}>
            <UnicornScene projectId="UtvhDctN8AjL6tvf1yKd" className="w-full h-full" fps={30} scale={0.75} dpi={1} />
          </Suspense>
        )}
        <div className="absolute inset-0 bg-black/50 pointer-events-none" />
        <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-[#050505] to-transparent pointer-events-none" />
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#050505] to-transparent pointer-events-none" />
      </div>

      <Header />

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/projelerim" element={<ProjectsPage />} />
      </Routes>
    </div>
  );
}
