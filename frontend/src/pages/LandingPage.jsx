import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Button } from "../components/ui/button";
import {
  CheckCircle2,
  Zap,
  Users,
  BarChart3,
  ArrowRight,
  Sun,
  Moon,
  FolderKanban,
  Clock,
  MessageSquare,
} from "lucide-react";

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const features = [
    {
      icon: FolderKanban,
      title: "Project Management",
      description: "Organize projects with Kanban boards, list views, and timeline tracking.",
    },
    {
      icon: CheckCircle2,
      title: "Task Tracking",
      description: "Create, assign, and track tasks with priorities, due dates, and subtasks.",
    },
    {
      icon: Users,
      title: "Team Collaboration",
      description: "Invite team members, assign roles, and collaborate in real-time.",
    },
    {
      icon: Clock,
      title: "Time Tracking",
      description: "Log hours, track progress, and generate time reports per project.",
    },
    {
      icon: MessageSquare,
      title: "Comments & Mentions",
      description: "Communicate with @mentions, comments, and activity feeds.",
    },
    {
      icon: BarChart3,
      title: "Analytics & Reports",
      description: "Dashboard insights, completion rates, and exportable reports.",
    },
  ];

  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-card/80 backdrop-blur-xl border-b border-border z-50">
        <div className="max-w-7xl mx-auto h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">P</span>
            </div>
            <span className="font-heading font-bold text-xl tracking-tight">ProFlow</span>
          </Link>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={toggleTheme} data-testid="theme-toggle">
              {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
            
            {isAuthenticated ? (
              <Button asChild data-testid="dashboard-btn">
                <Link to="/dashboard">Go to Dashboard</Link>
              </Button>
            ) : (
              <>
                <Button variant="ghost" asChild data-testid="login-btn">
                  <Link to="/login">Sign In</Link>
                </Button>
                <Button asChild data-testid="register-btn">
                  <Link to="/register">Get Started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 hero-gradient">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Zap className="w-4 h-4" />
            Project Management SaaS
          </div>
          
          <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Manage Projects with
            <span className="block text-primary">Clarity & Speed</span>
          </h1>
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10">
            ProFlow is a modern project management platform for teams. Organize tasks, 
            track time, collaborate with your team, and deliver projects on time.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" asChild data-testid="hero-get-started-btn">
              <Link to="/register">
                Start Free Trial
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-muted/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mb-4">
              Everything you need to manage projects
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Powerful features designed for modern teams. From task management to analytics.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="feature-card"
                style={{ animationDelay: `${index * 100}ms` }}
                data-testid={`feature-card-${index}`}
              >
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-heading font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mb-4">
            Ready to streamline your workflow?
          </h2>
          <p className="text-muted-foreground mb-8">
            Join teams already using ProFlow to deliver projects faster.
          </p>
          <Button size="lg" asChild data-testid="cta-get-started-btn">
            <Link to="/register">
              Get Started Free
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-primary rounded flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-xs">P</span>
            </div>
            <span className="font-heading font-semibold">ProFlow</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} ProFlow. Built for modern teams.
          </p>
        </div>
      </footer>
    </div>
  );
}
