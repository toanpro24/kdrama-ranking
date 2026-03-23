import { useNavigate } from "react-router-dom";
import "./index.css";

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="detail-page">
      <div className="not-found-page">
        <span className="not-found-code">404</span>
        <h1 className="not-found-title">Page Not Found</h1>
        <p className="not-found-text">The page you're looking for doesn't exist or has been moved.</p>
        <button className="not-found-btn" onClick={() => navigate("/")}>Back to Tier List</button>
      </div>
    </div>
  );
}
