import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Posts from './pages/Posts';
import Pages from './pages/Pages';
// import Comments from './pages/Comments';  // Hidden for now
import Imports from './pages/Imports';
import Overlap from './pages/Overlap';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="posts" element={<Posts />} />
          <Route path="pages" element={<Pages />} />
          {/* <Route path="comments" element={<Comments />} /> */}{/* Hidden for now */}
          <Route path="imports" element={<Imports />} />
          <Route path="overlap" element={<Overlap />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
